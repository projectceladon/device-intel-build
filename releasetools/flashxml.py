#!/usr/bin/env python

import os
import json
import copy
from optparse import OptionParser
from lxml import etree
import tempfile
import StringIO

# main Class to generate xml file from json configuration file
class FlashFileXml:

    def __init__(self, config, platform):
        self.flist = []
        flashtype = config['flashtype']
        self.xml = etree.Element('flashfile')
        self.xml.set('version', '1.0')
        self.add_sub(self.xml, 'id', flashtype)
        self.add_sub(self.xml, 'platform', platform)

    def add_sub(self, parent, name, text):
        sub = etree.SubElement(parent, name)
        sub.text = text

    def add_file(self, filetype, filename, version):
        if filename in self.flist:
            return
        cg = etree.SubElement(self.xml, 'code_group')
        cg.set('name', filetype)
        fl = etree.SubElement(cg, 'file')
        fl.set('TYPE', filetype)
        self.add_sub(fl, 'name', filename)
        self.add_sub(fl, 'version', version)

        self.flist.append(filename)

    def add_command(self, command, description, (timeout, retry, mandatory)):
        mandatory = {True: "1", False: "0"}[mandatory]
        cmd = etree.SubElement(self.xml, 'command')
        self.add_sub(cmd, 'string', command)
        self.add_sub(cmd, 'timeout', str(timeout))
        self.add_sub(cmd, 'retry', str(retry))
        self.add_sub(cmd, 'description', description)
        self.add_sub(cmd, 'mandatory', mandatory)

    def parse_command(self, commands):
        for cmd in commands:
            if 'target' in cmd:
                fname = cmd['target']
                shortname = fname.split('.')[0]
                self.add_file(shortname, fname, 'unspecified')
                cmd['pftname'] = '$' + shortname.lower() + '_file'

        for cmd in commands:
            params = (cmd.get('timeout', 60000), cmd.get('retry', 2), cmd.get('mandatory', True))
            if cmd['type'] == 'fastboot':
                desc = cmd.get('desc', cmd['args'])
                command = 'fastboot ' + cmd['args']
                if 'pftname' in cmd:
                    command += ' ' + cmd['pftname']
            elif cmd['type'] == 'waitForDevice' or cmd['type'] == 'sleep':
                desc = cmd.get('desc', 'Sleep for ' + str(params[0] / 1000) + ' seconds')
                command = 'sleep'
            else:
                continue
            self.add_command(command, desc, params)

    def finish(self):
        tree = etree.ElementTree(self.xml)
        tf = StringIO.StringIO()
        tree.write(tf, xml_declaration=True, encoding="utf-8", pretty_print=True)
        data = tf.getvalue()
        tf.close()
        return data

# main Class to generate json file from json configuration file
class FlashFileJson:

    def __init__(self, config):
        self.flist = []

        self.configurations = config
        out_cfg = copy.deepcopy(config)
        for cfg_name, cfg in out_cfg.items():
            cfg.pop('commands')
            cfg.pop('subgroup')
            cfg['name'] = cfg_name

        self.flash = {'version': '2.0', 'osplatform': 'android',
                     'parameters': {}, 'configurations': out_cfg, 'commands': []}

    def add_file(self, shortname, filename):
        if filename in self.flist:
            return
        self.flist.append(filename)
        new = {'type': 'file', 'name': shortname, 'value': filename, 'description': filename}
        self.flash['parameters'][shortname] = new

    def add_command(self, new, cmd):

        new['restrict'] = []
        for cfg_name, cfg in self.configurations.items():
            if cfg['commands'] != self.cmd_grp:
                continue
            if not filter_command(cmd, None, None, cfg['subgroup']):
                continue
            new['restrict'].append(cfg_name)
        if len(new['restrict']):
            self.flash['commands'].append(new)

    def parse_command(self, commands, variant, platform):
        for cmd in commands:
            if 'target' in cmd:
                fname = cmd['target']
                shortname = fname.split('.')[0].lower()
                self.add_file(shortname, fname)
                cmd['pftname'] = '${' + shortname + '}'

        for cmd in commands:
            new = {}
            new['timeout'] = cmd.get('timeout', 60000)
            new['retry'] = cmd.get('retry', 2)
            new['mandatory'] = cmd.get('mandatory', True)

            if not filter_command(cmd, variant, platform, None):
                continue

            if cmd['type'] == 'fastboot':
                new['description'] = cmd.get('desc', cmd['args'])
                new['tool'] = 'fastboot'
                new['args'] = cmd['args']
                if 'pftname' in cmd:
                    new['args'] += ' ' + cmd['pftname']
            elif cmd['type'] == 'waitForDevice':
                new['state'] = cmd.get('state','pos')
                new['description'] = cmd.get('desc', 'Wait for device to enumerate in ' + new['state'])
                new['tool'] = 'waitForDevice'
            elif cmd['type'] == 'sleep':
                new['description'] = cmd.get('desc', 'Wait for ' + str(new['timeout']/1000) + ' seconds')
                new['tool'] = 'sleep'
                new['duration'] = new['timeout']
            else:
                continue
            self.add_command(new, cmd)

    def parse_command_grp(self, cmd_groups, variant, platform):
        for grp in cmd_groups:
            self.cmd_grp = grp
            self.parse_command(cmd_groups[grp], variant, platform)

    def finish(self):
        return json.dumps({'flash': self.flash}, indent=4, sort_keys=True)

def filter_command(cmd, variant, platform, subgroup):
    # You can filter-out items by prefixing with !. So cmd["!platform"] matches all platforms
    # except those in the list
    for k, v in [('variant', variant), ('restrict', subgroup), ('platform', platform)]:
        nk = "!" + k

        if not v:
            continue
        if k in cmd and v not in cmd[k]:
            return False
        if nk in cmd and v in cmd[nk]:
            return False
    return True


def parse_config(conf, variant, platform):
    results = []

    for c in conf['config']:
        print "Generating", c['filename']

        # Special case for json, because it can have multiple configurations
        if c['filename'][-5:] == '.json':
            f = FlashFileJson(conf['configurations'])
            f.parse_command_grp(conf['commands'], variant, platform)
            results.append((c['filename'], f.finish()))
            continue

        if c['filename'][-4:] == '.xml':
            f = FlashFileXml(c, platform)
        elif c['filename'][-4:] == '.cmd':
            f = FlashFileCmd(c)

        commands = conf['commands'][c['commands']]
        commands = [cmd for cmd in commands if
                filter_command(cmd, variant, platform, c['subgroup'])]

        f.parse_command(commands)
        results.append((c['filename'], f.finish()))
    return results


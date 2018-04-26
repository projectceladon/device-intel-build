#!/usr/bin/env python

import os
import json
import copy
from optparse import OptionParser
import xml.etree.ElementTree as etree
from xml.dom import minidom
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
            if 'target' in cmd and 'format' not in cmd['args']:
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
        tree.write(tf, xml_declaration=True, encoding="utf-8")
        data = tf.getvalue()
        tf.close()
        pretty = minidom.parseString(data)
        return pretty.toprettyxml(encoding="utf-8")

# main Class to generate json file from json configuration file
class FlashFileJson:

    def __init__(self, config):
        self.flist = {}

        self.configurations = config
        out_cfg = copy.deepcopy(config)
        for cfg_name, cfg in out_cfg.items():
            cfg.pop('commands')
            if 'subgroup' in cfg:
                cfg.pop('subgroup')
            cfg['name'] = cfg_name

        self.flash = {'version': '2.0', 'osplatform': 'android',
                     'parameters': {}, 'configurations': out_cfg, 'commands': []}

    def add_file(self, shortname, filename, source):
        if filename in self.flist:
            return
        self.flist[filename] = source
        new = {'type': 'file', 'name': shortname, 'value': filename, 'description': filename}
        self.flash['parameters'][shortname] = new

    def add_command(self, new, cmd):

        new['restrict'] = []
        for cfg_name, cfg in self.configurations.items():
            if cfg['commands'] != self.cmd_grp:
                continue
            if not filter_command(cmd, None, None, cfg.get('subgroup', 'default')):
                continue
            new['restrict'].append(cfg_name)
        if len(new['restrict']):
            self.flash['commands'].append(new)

    def parse_command(self, commands, options, variant, platform):
        for cmd in commands:
            if not filter_command(cmd, variant, platform, None):
                continue
            if 'target' in cmd:
                if not isinstance(cmd['target'], list):
                    cmd['target'] = [cmd['target']]
                if 'format' not in cmd['args']:
                    cmd['pftname'] = []
                    for f in cmd['target']:
                        shortname = f.split('.')[0].lower()
                        self.add_file(shortname, f, cmd['source'])
                        cmd['pftname'].append('${' + shortname + '}')

        for cmd in commands:
            new = {}
            new['timeout'] = cmd.get('timeout', 60000)
            new['retry'] = cmd.get('retry', 2)
            new['mandatory'] = cmd.get('mandatory', True)
            if 'group' in cmd:
                new['group'] = cmd['group']

            if not filter_command(cmd, variant, platform, None):
                continue

            if cmd['type'] in ('fastboot', 'dldr'):
                new['description'] = cmd.get('desc', cmd['args'])
                new['tool'] = cmd['type']
                if options and 'fastboot' in options:
                    for opt in options['fastboot']:
                        new[opt] = options['fastboot'][opt]
                new['args'] = cmd['args']
                if 'pftname' in cmd:
                    if '$' in new['args']:
                        for i, f in enumerate(cmd['pftname']):
                            new['args'] = new['args'].replace('$' + str(i + 1), f)
                    else:
                        new['args'] += ' ' + cmd['pftname'][0]
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

    def parse_command_grp(self, cmd_groups, options, variant, platform):
        for grp in cmd_groups:
            self.cmd_grp = grp
            self.parse_command(cmd_groups[grp], options, variant, platform)

    def add_groups(self, groups):
        self.flash['groups'] = groups

    def files(self):
        return self.flist

    def finish(self):
        return json.dumps({'flash': self.flash}, indent=4, sort_keys=True)

# main Class to generate installer cmd file from json configuration file
class FlashFileCmd:
    def __init__(self, config):
        self.cmd = ""

    def parse_command(self, commands):
        for cmd in commands:
            if cmd['type'] == 'fastboot':
                self.cmd += cmd['args']
                if 'target' in cmd and 'format' not in cmd['args']:
                    self.cmd += " " + cmd['target'][0]
                self.cmd += "\n"

    def finish(self):
        return self.cmd


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
    files = []

    for c in conf['config']:
        print "Generating", c['filename']

        # Special case for json, because it can have multiple configurations
        if c['filename'][-5:] == '.json':
            f = FlashFileJson(conf['configurations'])
            options = conf.get('options', "")
            f.parse_command_grp(conf['commands'], options, variant, platform)
            if 'groups' in conf:
                f.add_groups(conf['groups'])
            results.append((c['filename'], f.finish()))
            files = [[src, file] for file, src in f.files().items()]
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
    return results, files


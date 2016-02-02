#!/usr/bin/env python

import os
import json
import re

# main Class to generate json file from json configuration file
class FlashFileJson:

    def __init__(self, config, mv_config_default):
        self.flist = {}
        self.flash = {'version': '2.1',
                      'groups': {},
                      'osplatform': 'android',
                      'parameters': {},
                      'configurations': {},
                      'commands': []}
        self.prop = {}
        self.mv_args = {}
        self.mv_config_default = mv_config_default
        self.extracts = {'psi': '.fls_ID0_PSI_LoadMap0.bin',
                         'slb': '.fls_ID0_SLB_LoadMap0.bin',
                         'hypervisor': '.fls_ID0_CODE_LoadMap0.bin',
                         'vrl': '.fls_ID0_PSI_LoadMap0.bin'}
        self.default_params = {"timeout":60000, "retry":2, "mandatory":True}

    def add_file(self, shortname, target, source, file_type):
        filename = os.path.basename(target)
        if filename in self.flist:
            return
        if "mvconfig_" in filename and re.split("mvconfig_|_signed|\.fls", filename)[1] != self.mv_config_default:
            target = "mvconfigs/" + filename
        if file_type == "file":
            self.flist[target] = source
        new = {'type': file_type, 'name': shortname, 'value': target, 'description': filename}
        self.flash['parameters'][shortname] = new

    def add_configuration(self, config, default):
        new = {config['config_name']: {}}
        for key in config:
            if key != 'config_name':
                new[config['config_name']][key] = config[key]
        new[config['config_name']]['default'] = default
        self.flash['configurations'].update(new)


    def add_command(self, tool, args, description, restrict, (timeout, retry, mandatory)):
        new = {'tool': tool,
               'args': args,
               'description': description,
               'timeout': timeout,
               'retry': retry,
               'mandatory': mandatory,
               'restrict': [restrict]}
        self.flash['commands'].append(new)

    def add_popup(self, ptype, description, restrict):
        new = {'tool': 'popup',
               'type': ptype,
               'description': description,
               'restrict': [restrict]}
        self.flash['commands'].append(new)

    def add_buildproperties(self, path):

        with open(os.path.join(path, 'build.prop'), 'r') as f:
            for line in f.readlines():
                if not line.startswith("#") and line.count("=") == 1:
                    name, value = line.strip().split("=")
                    self.prop[name] = value

    def parse_command(self, commands):

        for cmd in commands:
            if cmd['type'] in ['fls']:
                fname = os.path.basename(cmd['target'])
                shortname = fname.split('.')[0].lower()
                self.add_file(shortname, cmd['target'], cmd['source'], 'file')
                cmd['pftname'] = '${' + shortname + '}'

                if 'core' in cmd:
                    for s in cmd['core'].split(','):
                        self.mv_args[s + '_fls_config'] += cmd['pftname'] + ' '
                else:
                    for mv in self.mv_args:
                        self.mv_args[mv] += cmd['pftname'] + ' '

                if 'fastboot' in cmd and cmd['fastboot'] == "yes":
                    extracted_suff = self.extracts.get(cmd['partition'], '.fls_ID0_CUST_LoadMap0.bin')
                    fname_temp = re.split("_signed|\.fls", fname)[0] + extracted_suff
                    shortname_temp = shortname + '_temp'
                    self.add_file(shortname_temp, fname_temp, cmd['source'], 'temporary_file')

                    params = (cmd.get('timeout', self.default_params['timeout']), cmd.get('retry', self.default_params['retry']), cmd.get('mandatory', self.default_params['mandatory']))
                    self.add_command('flsTool', ' -x ${' + shortname + '} --replace -o ${' + shortname_temp + '}', 'Extract image parts from ' + fname, 'fastboot_config', params)
                    self.add_command('fastboot', ' flash ' +  cmd['partition'] + ' ${' + shortname_temp + '}/'  + fname_temp, 'Flashing ' +  cmd['partition'] + ' with fastboot', 'fastboot_config', params)

            if cmd['type'] == 'info':
                fname = os.path.basename(cmd['target'])
                shortname = fname.split('.')[0].lower()
                self.add_file(shortname, cmd['target'], cmd['source'], 'file')
                continue

        tools = 'flsDownloader'
        for config_name in self.flash['configurations']:
            c = self.flash['configurations'][config_name]
            if config_name == "fastboot_config":
                self.add_command('fastboot', ' flashing lock', 'lock the device', config_name, (self.default_params['timeout'], self.default_params['retry'], self.default_params['mandatory']))
                self.add_command('fastboot', ' continue ', 'fastboot continue', config_name, (self.default_params['timeout'], self.default_params['retry'], self.default_params['mandatory']))
                continue
            mv_desc = "Flashing " + c['name'] + " image"
            params = (c.get('timeout'), c.get('retry', self.default_params['retry']), c.get('mandatory', self.default_params['mandatory']))
            if 'erase' in config_name:
                self.mv_args[config_name] = '--erase-mode=1 ' + self.mv_args[config_name]
                self.add_popup('warn', "This configuration will erase *all* your NVM, including calibration data. Unplug now your board to abort", config_name)
            self.add_command(tools, self.mv_args[config_name], mv_desc, config_name, params)


    def parse_configuration(self, configurations):
        for config in configurations:
            default = False
            if config['config_name'] == "fastboot_config":
                self.add_command('fastboot', ' flashing unlock', 'unlock the device', config['config_name'], (self.default_params['timeout'], self.default_params['retry'], self.default_params['mandatory']))
            else:
                self.mv_args[config['config_name']] = ""
                if config['config_name'].split("_fls_config")[0] == self.mv_config_default:
                    default = True

            self.add_configuration(config, default)

    def files(self):
        return self.flist

    def finish(self):
        return json.dumps({'flash': self.flash, 'build_info': self.prop}, indent=4, sort_keys=True)


def parse_config(conf, variant, platform, mv_config_default, prop_path):

    results = []
    files = []

    for c in conf['config']:
        if c['filename'][-5:] == '.json':
            f = FlashFileJson(c, mv_config_default)
        elif c['filename'][-4:] == '.xml':
            print "warning: xml format not supported. Skipping."
            continue
        elif c['filename'][-4:] == '.cmd':
            print "warning: cmd format not supported. Skipping."
            continue
        elif c['filename'][-3:] == '.sh':
            print "warning: sh format not supported. Skipping."
            continue
        else:
            print "warning: unknown format. Skipping."
            continue

        commands = conf['commands']
        commands = [cmd for cmd in commands if not 'restrict' in cmd or c['name'] in cmd['restrict']]

        f.add_buildproperties(prop_path)
        if c['filename'][-5:] == '.json':
            configurations = conf['configurations']
            f.parse_configuration(configurations)

        f.parse_command(commands)

        results.append((c['filename'], f.finish()))
        files = [[src, file] for file, src in f.files().items()]

    return results, files


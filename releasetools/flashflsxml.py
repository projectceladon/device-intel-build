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

    def add_file(self, shortname, target, source):
        filename = os.path.basename(target)
        if filename in self.flist:
            return
        if "mvconfig_" in filename and re.split("mvconfig_|_signed|\.fls", filename)[1] != self.mv_config_default:
            target = "mvconfigs/" + filename
        self.flist[target] = source
        new = {'type': 'file', 'name': shortname, 'value': filename, 'description': filename}
        self.flash['parameters'][shortname] = new

    def add_configuration(self, config_name, brief, description, groupsState, name, parameters, startState, default):
        new = {config_name: {'brief': brief,
                            'description': description,
                            'groupsState': groupsState,
                            'name': name,
                            'parameters': parameters,
                            'startState': startState,
                            'default': default
                            }
              }
        self.flash['configurations'].update(new)


    def add_command(self, tool, args, description, restrict, (timeout, retry, mandatory)):
        new = {'tool': tool,
               'args': args,
               'description': description,
               'timeout': timeout,
               'retry': retry,
               'mandatory': mandatory,
               'restrict': restrict}
        self.flash['commands'].append(new)

    def add_popup(self, ptype, description, restrict):
        new = {'tool': 'popup',
               'type': ptype,
               'description': description,
               'restrict': restrict}
        self.flash['commands'].append(new)

    def add_buildproperties(self, buildprop):

        with open(os.path.join(os.environ['ANDROID_PRODUCT_OUT'], buildprop), 'r') as f:
            for line in f.readlines():
                if not line.startswith("#") and line.count("=") == 1:
                    name, value = line.strip().split("=")
                    self.prop[name] = value

    def parse_command(self, commands):

        for cmd in commands:
            if cmd['type'] in ['fls']:
                fname = os.path.basename(cmd['target'])
                shortname = fname.split('.')[0].lower()
                self.add_file(shortname, cmd['target'], cmd['source'])
                cmd['pftname'] = '${' + shortname + '}'

                if 'core' in cmd:
                    for s in cmd['core'].split(','):
                        self.mv_args[s + '_fls_config'] += cmd['pftname'] + ' '
                else:
                    for mv in self.mv_args:
                        self.mv_args[mv] += cmd['pftname'] + ' '

            if cmd['type'] == 'prop':
                self.add_buildproperties(cmd['target'])
                continue

        tools = 'flsDownloader'
        params = (cmd.get('timeout', 60000), cmd.get('retry', 2), cmd.get('mandatory', True))
        for config_name in self.flash['configurations']:
            c = self.flash['configurations'][config_name]
            mv_desc = "Flashing " + c['name'] + " image"
            if 'erase' in config_name:
                self.mv_args[config_name] = '--erase-mode=1 ' + self.mv_args[config_name]
                self.add_popup('warn', "This configuration will erase *all* your NVM, including calibration data. Unplug now your board to abort", config_name)
            self.add_command(tools, self.mv_args[config_name], mv_desc, config_name, params)


    def parse_configuration(self, configurations):
        for config in configurations:
            self.mv_args[config['config_name']] = ""
            if config['config_name'].split("_fls_config")[0] == self.mv_config_default:
                default = True
            else:
                default = False

            self.add_configuration(config['config_name'], config['brief'], config['description'], config['groupsState'], config['name'], config['parameters'], config['startState'], default)

    def files(self):
        return self.flist

    def finish(self):
        return json.dumps({'flash': self.flash, 'build_info': self.prop}, indent=4, sort_keys=True)


def parse_config(conf, variant, platform, mv_config_default):

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

        if c['filename'][-5:] == '.json':
            configurations = conf['configurations']
            f.parse_configuration(configurations)

        f.parse_command(commands)

        results.append((c['filename'], f.finish()))
        files = [[src, file] for file, src in f.files().items()]

    return results, files


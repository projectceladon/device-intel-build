#!/usr/bin/env python

import os
import json

# main Class to generate json file from json configuration file
class FlashFileJson:

    def __init__(self, config):
        self.flist = {}
        self.flash = {'version': '2.1',
                      'groups': {},
                      'osplatform': 'android',
                      'parameters': {},
                      'configurations': {},
                      'commands': []}
        self.prop = {}

    def add_file(self, shortname, filename, source):
        if filename in self.flist:
            return
        self.flist[filename] = source
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
               'timeout': 600000,
               'retry': retry,
               'mandatory': mandatory,
               'restrict': restrict}
        self.flash['commands'].append(new)

    def add_buildproperties(self, buildprop):

        with open(os.path.join(os.environ['ANDROID_PRODUCT_OUT'], buildprop), 'r') as f:
            for line in f.readlines():
                if not line.startswith("#") and line.count("=") == 1:
                    name, value = line.strip().split("=")
                    self.prop[name] = value

    def parse_command(self, commands):

        up_args = ''
        smp_args = ''

        for cmd in commands:
            if cmd['type'] in ['fls']:
                if (cmd['core'] in ['up,smp']) or (cmd['core'] in ['up']):
                    fname = os.path.basename(cmd['target'])
                    shortname = fname.split('.')[0].lower()
                    self.add_file(shortname, fname, cmd['source'])
                    cmd['pftname'] = '${' + shortname + '}'
                    up_args = up_args + ' ' + cmd['pftname']

                if (cmd['core'] in ['up,smp']) or (cmd['core'] in ['smp']):
                    fname = os.path.basename(cmd['target'])
                    shortname = fname.split('.')[0].lower()
                    self.add_file(shortname, fname, cmd['source'])
                    cmd['pftname'] = '${' + shortname + '}'
                    smp_args = smp_args + ' ' + cmd['pftname']

            if cmd['type'] == 'prop':
                self.add_buildproperties(cmd['target'])
                continue

        params = (cmd.get('timeout', 60000), cmd.get('retry', 2), cmd.get('mandatory', True))
        tools = 'flsDownloader'
        up_desc = cmd.get('desc', 'Flashing ' + 'UP' + 'FLS' + ' image')
        smp_desc = cmd.get('desc', 'Flashing ' + 'SMP' + 'FLS' + ' image')
        self.add_command(tools, up_args, up_desc, 'up_fls_config', params)
        self.add_command(tools, smp_args, smp_desc, 'smp_fls_config', params)
        smp_erase_desc = cmd.get('desc', 'Erase & Flashing ' + 'SMP' + 'FLS' + ' image')
        self.add_command(tools, '--erase-mode=2 ' + smp_args, smp_desc, 'smp_fls_erase_config', params)


    def parse_configuration(self, configurations):
        for config in configurations:
            if config['config_name'] in ['smp_fls_config']:
                default = True
            else:
                default = False

            self.add_configuration(config['config_name'], config['brief'], config['description'], config['groupsState'], config['name'], config['parameters'], config['startState'], default)

    def files(self):
        return self.flist

    def finish(self):
        return json.dumps({'flash': self.flash, 'build_info': self.prop}, indent=4, sort_keys=True)


def parse_config(conf, variant, platform):

    results = []
    files = []

    for c in conf['config']:
        if c['filename'][-5:] == '.json':
            f = FlashFileJson(c)
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

        f.parse_command(commands)

        if c['filename'][-5:] == '.json':
            configurations = conf['configurations']
            f.parse_configuration(configurations)

        results.append((c['filename'], f.finish()))
        files = [[src, file] for file, src in f.files().items()]

    return results, files


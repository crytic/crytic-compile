from . import defaults_flag_in_config

def init(parser):

    group_solc = parser.add_argument_group('Compile options')
    group_solc.add_argument('--compile-force-framework',
                            help='Force the compile to a given framework (truffle, embark, dapp, etherlime, etherscan)',
                            action='store',
                            default=defaults_flag_in_config['compile_force_framework'])

    group_solc.add_argument('--compile-remove-metadata',
                            help='Remove the metadata from the bytecodes',
                            action='store_true',
                            default=defaults_flag_in_config['compile_remove_metadata'])

    group_solc.add_argument('--compile-custom-build',
                            help='Replace platform specific build command',
                            action='store',
                            default=defaults_flag_in_config['compile_custom_build'])

    init_solc(parser)
    init_truffle(parser)
    init_embark(parser)
    init_dapp(parser)
    init_etherlime(parser)

def init_solc(parser):
    group_solc = parser.add_argument_group('Solc options')
    group_solc.add_argument('--solc',
                            help='solc path',
                            action='store',
                            default=defaults_flag_in_config['solc'])

    group_solc.add_argument('--solc-remaps',
                            help='Add remapping',
                            action='store',
                            default=defaults_flag_in_config['solc_remaps'])

    group_solc.add_argument('--solc-args',
                            help='Add custom solc arguments. Example: --solc-args "--allow-path /tmp --evm-version byzantium".',
                            action='store',
                            default=defaults_flag_in_config['solc_args'])

    group_solc.add_argument('--solc-disable-warnings',
                            help='Disable solc warnings',
                            action='store_true',
                            default=defaults_flag_in_config['solc_disable_warnings'])

    group_solc.add_argument('--solc-working-dir',
                            help='Change the default working directory',
                            action='store',
                            default=defaults_flag_in_config['solc_working_dir'])

def init_truffle(parser):
    group_truffle = parser.add_argument_group('Truffle options')
    group_truffle.add_argument('--truffle-ignore-compile',
                               help='Do not run truffle compile',
                               action='store_true',
                               dest='truffle_ignore_compile',
                               default=defaults_flag_in_config['truffle_ignore_compile'])

    group_truffle.add_argument('--truffle-build-directory',
                               help='Use an alternative truffle build directory',
                               action='store',
                               dest='truffle_build_directory',
                               default=defaults_flag_in_config['truffle_build_directory'])

    group_truffle.add_argument('--truffle-version',
                               help='Use a local Truffle version (with npx)',
                               action='store',
                               default=defaults_flag_in_config['truffle_version'])
    return group_truffle

def init_embark(parser):
    group_embark = parser.add_argument_group('Embark options')
    group_embark.add_argument('--embark-ignore-compile',
                              help='Do not run embark build',
                              action='store_true',
                              dest='embark_ignore_compile',
                              default=defaults_flag_in_config['embark_ignore_compile'])

    group_embark.add_argument('--embark-overwrite-config',
                              help='Install @trailofbits/embark-contract-export and add it to embark.json',
                              action='store_true',
                              default=defaults_flag_in_config['embark_overwrite_config'])

def init_dapp(parser):
    group_dapp = parser.add_argument_group('Dapp options')
    group_dapp.add_argument('--dapp-ignore-compile',
                            help='Do not run dapp build',
                            action='store_true',
                            dest='dapp_ignore_compile',
                            default=defaults_flag_in_config['dapp_ignore_compile'])

def init_etherlime(parser):
    group_etherlime = parser.add_argument_group('Etherlime options')
    group_etherlime.add_argument('--etherlime-ignore-compile',
                                 help='Do not run etherlime compile',
                                 action='store_true',
                                 dest='etherlime_ignore_compile',
                                 default=defaults_flag_in_config['etherlime_ignore_compile'])

    group_etherlime.add_argument('--etherlime-compile-arguments',
                                 help='Add arbitrary arguments to etherlime compile (note: [dir] is the the directory provided to crytic-compile)',
                                 action='store_true',
                                 dest='etherlime_compile_arguments',
                                 default=defaults_flag_in_config['etherlime_compile_arguments'])


import unittest
import os

try:
    import unittest.mock as mock
except ImportError:
    import mock

from routersploit.interpreter import RoutersploitInterpreter
from routersploit.test import RoutersploitTestCase


class RoutersploitInterpreterTest(RoutersploitTestCase):

    def setUp(self):
        RoutersploitInterpreter.setup = mock.Mock()
        self.interpreter = RoutersploitInterpreter()
        self.interpreter.current_module = mock.MagicMock()
        self.raw_prompt_default = "\001\033[4m\002rsf\001\033[0m\002 > "
        self.module_prompt_default = lambda x: "\001\033[4m\002rsf\001\033[0m\002 (\001\033[91m\002{}\001\033[0m\002) > ".format(x)

    def prepare_prompt_env_variables(self, raw_prompt=None, module_prompt=None):
        if raw_prompt:
            os.environ["RSF_RAW_PROMPT"] = raw_prompt
        else:
            try:
                os.environ["RSF_RAW_PROMPT"]
            except KeyError:
                pass

        if module_prompt:
            os.environ["RSF_MODULE_PROMPT"] = module_prompt
        else:
            try:
                del os.environ["RSF_MODULE_PROMPT"]
            except KeyError:
                pass

        getattr(self.interpreter, '_{}__parse_prompt'.format(self.interpreter.__class__.__name__))()

    @mock.patch('routersploit.utils.print_success')
    def test_command_set(self, mock_print_success):
        rhost, new_rhost_value = 'rhost_value', "new_rhost_value"
        port, new_port_value = 'port_value', "new_port_value"

        self.interpreter.current_module.options = ['rhost', 'port']
        self.interpreter.current_module.rhost = rhost
        self.interpreter.current_module.port = port
        self.assertEqual(self.interpreter.current_module.rhost, rhost)
        self.assertEqual(self.interpreter.current_module.port, port)

        self.interpreter.command_set('rhost {}'.format(new_rhost_value))
        self.interpreter.command_set('port {}'.format(new_port_value))
        self.assertEqual(self.interpreter.current_module.rhost, new_rhost_value)
        self.assertEqual(self.interpreter.current_module.port, new_port_value)
        self.assertEqual(
            mock_print_success.mock_calls,
            [mock.call({'rhost': new_rhost_value}), mock.call({'port': new_port_value})]
        )

    @mock.patch('routersploit.utils.print_error')
    def test_command_set_unknown_option(self, mock_print_error):
        unknown_option = "unknown"
        del self.interpreter.current_module.unknown
        known_options = ['known_option_1', 'known_option_2']
        self.interpreter.current_module.options = known_options

        self.interpreter.command_set('{} doesnt_matter_value'.format(unknown_option))

        self.assertEqual(
            mock_print_error.mock_calls,
            [mock.call("You can't set option '{}'.\nAvailable options: {}".format(unknown_option, known_options))]
        )

    def test_command_run(self):
        with mock.patch.object(self.interpreter.current_module, 'run') as mock_run:
            self.interpreter.command_run()
            mock_run.assert_called_once_with()

    @mock.patch('routersploit.utils.print_success')
    def test_command_check_target_vulnerable(self, mock_print_success):
        with mock.patch.object(self.interpreter.current_module, 'check') as mock_check:
            mock_check.return_value = True
            self.interpreter.command_check()
            mock_check.assert_called_once_with()
            mock_print_success.assert_called_once_with('Target is vulnerable')

    @mock.patch('routersploit.utils.print_error')
    def test_command_check_target_not_vulnerable(self, print_error):
        with mock.patch.object(self.interpreter.current_module, 'check') as mock_check:
            mock_check.return_value = False
            self.interpreter.command_check()
            mock_check.assert_called_once_with()
            print_error.assert_called_once_with('Target is not vulnerable')

    @mock.patch('routersploit.utils.print_status')
    def test_command_check_target_could_not_be_verified_1(self, print_status):
        with mock.patch.object(self.interpreter.current_module, 'check') as mock_check:
            mock_check.return_value = "something"
            self.interpreter.command_check()
            mock_check.assert_called_once_with()
            print_status.assert_called_once_with('Target could not be verified')

    @mock.patch('routersploit.utils.print_status')
    def test_command_check_target_could_not_be_verified_2(self, print_status):
        with mock.patch.object(self.interpreter.current_module, 'check') as mock_check:
            mock_check.return_value = None
            self.interpreter.command_check()
            mock_check.assert_called_once_with()
            print_status.assert_called_once_with('Target could not be verified')

    @mock.patch('routersploit.utils.print_error')
    def test_command_check_not_supported_by_module(self, print_error):
        with mock.patch.object(self.interpreter.current_module, 'check') as mock_check:
            exception = NotImplementedError("Not available")
            mock_check.side_effect = exception
            self.interpreter.command_check()
            mock_check.assert_called_once_with()
            print_error.assert_called_once_with(exception)

    @mock.patch('sys.exc_info')
    @mock.patch('traceback.format_exc')
    @mock.patch('routersploit.utils.print_error')
    def test_command_run_exception_during_exploit_execution(self, mock_print_error, mock_format_exc, mock_exc_info):
        with mock.patch.object(self.interpreter.current_module, 'run') as mock_run:
            mock_run.side_effect = RuntimeError
            mock_format_exc.return_value = stacktrace = "stacktrace"
            mock_exc_info.return_value = info = "info"

            self.interpreter.command_run()
            mock_run.assert_called_once_with()
            mock_format_exc.assert_called_once_with(info)
            mock_print_error.assert_called_once_with(stacktrace)

    def test_command_back(self):
        self.assertIsNotNone(self.interpreter.current_module)
        self.interpreter.command_back()
        self.assertIsNone(self.interpreter.current_module)

    def test_custom_raw_prompt(self):
        self.prepare_prompt_env_variables(raw_prompt="***{host}***")
        self.interpreter.current_module = None
        self.assertEqual("***rsf***", self.interpreter.prompt)

    def test_default_raw_prompt_no_env_variable(self):
        self.prepare_prompt_env_variables()
        self.interpreter.current_module = None
        self.assertEqual(self.raw_prompt_default, self.interpreter.prompt)

    def test_default_raw_prompt_wrong_env_variable_format(self):
        self.prepare_prompt_env_variables(raw_prompt="wrong_format >")  # no '{host}' substring
        self.interpreter.current_module = None
        self.assertEqual(self.raw_prompt_default, self.interpreter.prompt)

    def test_custom_module_prompt(self):
        self.prepare_prompt_env_variables(module_prompt="*{host}*{module} >>>")
        module_name = "module_name"
        self.interpreter.current_module._MagicMock__info__ = {'name': module_name}
        self.assertEqual("*rsf*{} >>>".format(module_name), self.interpreter.prompt)

    def test_default_module_prompt_no_env_variable(self):
        self.prepare_prompt_env_variables()
        name = "current_module_name"
        self.interpreter.current_module._MagicMock__info__ = {'name': name}
        self.assertEqual(self.module_prompt_default(name), self.interpreter.prompt)

    def test_default_module_prompt_wrong_env_variable_format_1(self):
        self.prepare_prompt_env_variables(raw_prompt="{module} >")  # no '{host}' substring
        name = "current_module_name"
        self.interpreter.current_module._MagicMock__info__ = {'name': name}
        self.assertEqual(self.module_prompt_default(name), self.interpreter.prompt)

    def test_default_module_prompt_wrong_env_variable_format_2(self):
        self.prepare_prompt_env_variables(module_prompt="{host} >")  # no '{module}' substring
        name = "current_module_name"
        self.interpreter.current_module._MagicMock__info__ = {'name': name}
        self.assertEqual(self.module_prompt_default(name), self.interpreter.prompt)

    def test_module_prompt_module_has_no_metadata(self):
        del self.interpreter.current_module._MagicMock__info__
        self.assertEqual(self.module_prompt_default('UnnamedModule'), self.interpreter.prompt)

    def test_module_prompt_module_has_no_name_key_in_metadata(self):
        self.interpreter.current_module._MagicMock__info__ = {}
        self.assertEqual(self.module_prompt_default('UnnamedModule'), self.interpreter.prompt)

    def test_suggested_commands_with_loaded_module(self):
        self.assertEqual(
            self.interpreter.suggested_commands(),
            ['run', 'back', 'set ', 'setg ', 'show ', 'check', 'exec ', 'help', 'exit']  # Extra space at the end because of following param
        )

    def test_suggested_commands_without_loaded_module(self):
        self.interpreter.current_module = None
        self.assertEqual(
            self.interpreter.suggested_commands(),  # Extra space at the end because of following param
            ['use ', 'exec', 'help', 'exit']
        )

    @mock.patch('importlib.import_module')
    def test_command_use_01(self, mocked_import_module):
        """ Testing command_use()

        * Known Exploit
        * Known module
        """
        module_path = "exploits/foo/bar"
        self.interpreter.current_module = None
        self.interpreter.modules = [module_path, 'doo/pa/foo/bar']
        exploit_class = mock.MagicMock(name="password_disclosure_module")
        mocked_import_module.return_value = mocked_module = mock.MagicMock(name='module')
        mocked_module.Exploit = exploit_class

        self.interpreter.command_use(module_path)

        mocked_import_module.assert_called_once_with('routersploit.modules.exploits.foo.bar')
        self.assertEqual(self.interpreter.current_module, exploit_class())

    @mock.patch('importlib.import_module')
    def test_command_use_02(self, mocked_import_module):
        """ Testing command_use()

        * Known Exploit
        * Known module
        """
        module_path = "creds/foo/bar/baz"
        self.interpreter.current_module = None
        self.interpreter.modules = [module_path, 'doo/pa/foo/bar']
        exploit_class = mock.MagicMock(name="password_disclosure_module")
        mocked_import_module.return_value = mocked_module = mock.MagicMock(name='module')
        mocked_module.Exploit = exploit_class

        self.interpreter.command_use(module_path)

        mocked_import_module.assert_called_once_with('routersploit.modules.creds.foo.bar.baz')
        self.assertEqual(self.interpreter.current_module, exploit_class())

    @mock.patch('importlib.import_module')
    @mock.patch('routersploit.utils.print_error')
    def test_command_use_unknown_module(self, mocked_print_error, mocked_import_module):
        """ Testing command_use()

        * Unknown module
        """
        self.interpreter.current_module = None
        self.interpreter.modules = ['doo/pa/foo/bar']
        module_path = "creds/foo/bar/baz"
        mocked_import_module.side_effect = ImportError("Not working")

        self.interpreter.command_use(module_path)

        mocked_import_module.assert_called_once_with('routersploit.modules.creds.foo.bar.baz')

        mocked_print_error.assert_called_once_with(
            "Error during loading 'routersploit/modules/creds/foo/bar/baz'\n\n"
            "Error: Not working\n\n"
            "It should be valid path to the module. Use <tab> key multiple times for completion."
        )
        self.assertEqual(self.interpreter.current_module, None)

    @mock.patch('importlib.import_module')
    @mock.patch('routersploit.utils.print_error')
    def test_command_use_unknown_extension(self, mocked_print_error, mocked_import_module):
        """ Testing command_use()

        * Unknown Exploit
        * Known module
        """
        module_path = "exploits/foo/bar"
        self.interpreter.current_module = None
        self.interpreter.modules = [module_path, 'doo/pa/foo/bar']
        mocked_import_module.return_value = mocked_module = mock.MagicMock(name='module')
        del mocked_module.Exploit

        self.interpreter.command_use(module_path)

        mocked_import_module.assert_called_once_with('routersploit.modules.exploits.foo.bar')
        mocked_print_error.assert_called_once_with(
            "Error during loading 'routersploit/modules/exploits/foo/bar'\n\n"
            "Error: Exploit\n\n"
            "It should be valid path to the module. Use <tab> key multiple times for completion."
        )

        self.assertEqual(self.interpreter.current_module, None)

    @mock.patch('__builtin__.print')
    def test_command_show_info(self, mock_print):
        metadata = {
            'devices': 'target_desc',
            'authors': 'authors_desc',
            'references': 'references_desc',
            'description': 'description_desc',
            'name': 'name_desc'
        }
        description = "Elaborate description fo the module"
        self.interpreter.current_module.__doc__ = description
        self.interpreter.current_module._MagicMock__info__ = metadata

        self.interpreter.command_show('info')
        self.assertEqual(
            mock_print.mock_calls,
            [
                mock.call('\nName:'),
                mock.call('name_desc'),
                mock.call('\nDescription:'),
                mock.call('description_desc'),
                mock.call('\nDevices:'),
                mock.call('target_desc'),
                mock.call('\nAuthors:'),
                mock.call('authors_desc'),
                mock.call('\nReferences:'),
                mock.call('references_desc'),
                mock.call()]
            )

    @mock.patch('__builtin__.print')
    def test_command_show_info_module_with_no_metadata(self, mock_print):
        metadata = {}
        description = "Elaborate description fo the module"
        self.interpreter.current_module.__doc__ = description
        self.interpreter.current_module._MagicMock__info__ = metadata

        self.interpreter.command_show('info')
        self.assertEqual(
            mock_print.mock_calls,
            [
                mock.call()]
            )

    @mock.patch('__builtin__.print')
    def test_command_show_options(self, mock_print):
        exploit_attributes = {
            'target': 'target_desc',
            'port': 'port_desc',
            'foo': 'foo_desc',
            'bar': 'bar_desc',
            'baz': 'baz_desc'
        }
        self.interpreter.current_module.options = ['target', 'port', 'foo', 'bar', 'baz']
        self.interpreter.current_module.exploit_attributes.__getitem__.side_effect = lambda key: exploit_attributes[key]

        self.interpreter.current_module.foo = 1
        self.interpreter.current_module.bar = 2
        self.interpreter.current_module.baz = 3
        self.interpreter.current_module.target = '127.0.0.1'
        self.interpreter.current_module.port = 22

        self.interpreter.command_show('options')
        self.assertEqual(
            mock_print.mock_calls,
            [
                mock.call('\nTarget options:'),
                mock.call(),
                mock.call('   Name       Current settings     Description     '),
                mock.call('   ----       ----------------     -----------     '),
                mock.call('   target     127.0.0.1            target_desc     '),
                mock.call('   port       22                   port_desc       '),
                mock.call(),
                mock.call('\nModule options:'),
                mock.call(),
                mock.call('   Name     Current settings     Description     '),
                mock.call('   ----     ----------------     -----------     '),
                mock.call('   bar      2                    bar_desc        '),
                mock.call('   foo      1                    foo_desc        '),
                mock.call('   baz      3                    baz_desc        '),
                mock.call(),
                mock.call(),
            ]
        )

    @mock.patch('__builtin__.print')
    def test_command_show_options_when_there_is_no_module_opts(self, mock_print):
        exploit_attributes = {
            'target': 'target_desc',
            'port': 'port_desc',
        }
        self.interpreter.current_module.options = ['target', 'port']
        self.interpreter.current_module.exploit_attributes.__getitem__.side_effect = lambda key: exploit_attributes[key]

        self.interpreter.current_module.target = '127.0.0.1'
        self.interpreter.current_module.port = 22

        self.interpreter.command_show('options')
        self.assertEqual(
            mock_print.mock_calls,
            [
                mock.call('\nTarget options:'),
                mock.call(),
                mock.call('   Name       Current settings     Description     '),
                mock.call('   ----       ----------------     -----------     '),
                mock.call('   target     127.0.0.1            target_desc     '),
                mock.call('   port       22                   port_desc       '),
                mock.call(),
                mock.call(),
            ]
        )

    @mock.patch('__builtin__.print')
    def test_command_show_unknown_sub_command(self, mock_print):
        help_text = "Unknown command 'show unknown_sub_command'. You want to 'show info' or 'show options'?"

        self.interpreter.command_show('unknown_sub_command')
        self.assertEqual(
            mock_print.mock_calls,
            [mock.call(help_text)]
        )

    def test_if_command_run_has_module_required_decorator(self):
        self.assertIsDecorated(
            self.interpreter.command_run,
            "module_required"
        )

    def test_if_command_set_has_module_required_decorator(self):
        self.assertIsDecorated(
            self.interpreter.command_set,
            "module_required"
        )

    def test_if_command_show_has_module_required_decorator(self):
        self.assertIsDecorated(
            self.interpreter.command_show,
            "module_required"
        )

    def test_if_command_check_has_module_required_decorator(self):
        self.assertIsDecorated(
            self.interpreter.command_check,
            "module_required"
        )

    def test_command_exit(self):
        with self.assertRaises(EOFError):
            self.interpreter.command_exit()

    @mock.patch('os.system')
    def test_command_exec(self, mock_system):
        self.interpreter.command_exec("foo -bar")
        mock_system.assert_called_once_with("foo -bar")

    @mock.patch('__builtin__.print')
    def test_command_help(self, mock_print):
        self.interpreter.current_module = None
        self.interpreter.command_help()
        mock_print.assert_called_once_with(self.interpreter.global_help)

    @mock.patch('__builtin__.print')
    def test_command_help_with_module_loaded(self, mock_print):
        self.interpreter.command_help()

        self.assertEqual(
            mock_print.mock_calls,
            [
                mock.call(self.interpreter.global_help),
                mock.call("\n", self.interpreter.module_help),
            ]
        )

if __name__ == '__main__':
    unittest.main()

from collections import defaultdict
from contextlib import contextmanager
import glob
from imp import find_module, load_module
import os
import socket
import sys
import time

from porkchop.util import parse_config


class PorkchopPlugin(object):
  _cache = None
  _data = {}
  _lastrefresh = 0

  def __init__(self, config_file=None):
    self.refresh_interval = 60
    self.force_refresh = False
    self.config = parse_config(config_file) if config_file else {}

  @property
  def data(self):
    if self.should_refresh():
      self._data = self.get_data()
    return self._data

  @data.setter
  def data(self, value):
    self._data = value
    self._lastrefresh = time.time()
    self.force_refresh = False

  def gendict(self):
    return defaultdict(dict)

  def rateof(self, a, b, ival):
    delta = float(b) - float(a)
    return delta / ival if delta > 0 else 0

  def should_refresh(self):
    if self.force_refresh:
      return True

    if self._lastrefresh != 0:
      if time.time() - self._lastrefresh > self.refresh_interval:
        return True
      else:
        return False
    else:
      return True

  @contextmanager
  def tcp_socket(self, host, port):
    try:
      sock = socket.socket()
      sock.connect((host, port))
      yield sock
    except socket.error:
      raise
    finally:
      sock.close()

  @contextmanager
  def unix_socket(self, path):
    try:
      sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
      sock.connect(path)
      yield sock
    except socket.error:
      raise
    finally:
      sock.close()


class PorkchopPluginHandler(object):
  plugins = {}

  def __init__(self, config_dir, directory=None):
    self.config_dir = config_dir
    self.config = parse_config(os.path.join(self.config_dir, 'porkchop.ini'))
    if directory:
      self.plugins.update(self.load_plugins(directory))
    #Load default plugin directory
    here = os.path.abspath(os.path.dirname(__file__))
    self.plugins.update(self.load_plugins(os.path.join(here, 'plugins')))

  def load_plugins(self, directory):
    plugins = {}
    sys.path.insert(0, directory)

    try:
      to_load = [p.strip() for p in self.config['porkchop']['plugins'].split(',')]
    except:
      to_load = []

    for infile in glob.glob(os.path.join(directory, '*.py')):
      module_name = os.path.splitext(os.path.basename(infile))[0]
      if module_name != '__init__' and (not to_load or module_name in to_load):
        try:
          if module_name in sys.modules:
            continue
          found_ = find_module(module_name)
          mod_= load_module(module_name, *found_)
          plugin_ = getattr(mod_, '%sPlugin' % module_name.capitalize())
          config_file = os.path.join(self.config_dir, '%s.ini' % module_name)
          plugins[module_name] = plugin_(config_file)
        except ImportError:
          pass

    return plugins

def test_plugin_data(plugin_name):
  plugin_handler = PorkchopPluginHandler('')
  plugin_ = plugin_handler.plugins[plugin_name]
  return plugin_.get_data()

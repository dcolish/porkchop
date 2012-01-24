import ConfigParser

def parse_config(path):
  config = {}
  cp = ConfigParser.ConfigParser()
  cp.read(path)

  for s in cp.sections():
    config.setdefault(s, {})
    for o in cp.options(s):
      config[s][o] = cp.get(s, o)

  return config

from collections import defaultdict
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer, _quote_html
import json
from SocketServer import ThreadingMixIn
import sys
import urlparse

class GetHandler(BaseHTTPRequestHandler):
  def format_output(self, fmt, data):
    if fmt == 'json':
      return json.dumps(data)
    else:
      return '\n'.join(self.json_path(data))

  def json_path(self, data):
    results = []
    def path_helper(data, path, results):
      for key, val in data.iteritems():
        if type(val) in [dict, defaultdict] :
          path_helper(val, '/'.join((path, key)), results)
        else:
          results.append(('%s %s' % (('/'.join((path, key)))\
            .replace('.','_'), val)))

    path_helper(data, '', results)
    return results

  def do_GET(self):
    data = {}
    formats = {'json': 'application/json', 'text': 'text/plain'}
    request = urlparse.urlparse(self.path)

    try:
      (path, fmt) = request.path.split('.')
      if fmt not in formats.keys():
        fmt = 'text'
    except ValueError:
      path = request.path
    if self.headers.get('accept', False) == 'application/json':
        fmt = 'json'
        self.error_content_type = 'application/json'
    else:
        fmt = 'text'

    if self.headers.get('x-porkchop-refresh', False):
      force_refresh = True
    else:
      force_refresh = False

    module = path.split('/')[1]

    try:
      if module:
        plugin = self.server.plugins[module]
        plugin.force_refresh = force_refresh
        self.log_message('Calling plugin: %s with force=%s' % (module, force_refresh))
        data.update({module: plugin.data})
      else:
        for plugin_name, plugin in self.server.plugins.items():
          try:
            plugin.force_refresh = force_refresh
            self.log_message('Calling plugin: %s with force=%s' % (plugin_name, force_refresh))
            # if the plugin has no data,
            # it'll only have one key:
            # refreshtime
            if len(plugin.data) > 1:
              data.update({plugin_name: plugin.data})
          except:
            self.log_error('Error loading plugin: name=%s exception=%s', plugin_name, sys.exc_info())

      if len(data):
        self.send_response(200)
        self.send_header('Content-Type', formats[fmt])
        self.end_headers()
        self.wfile.write(self.format_output(fmt, data) + '\n')
      else:
        # FIXME:dc: this is not actually a failure to load plugings, just no new
        # data was returned
        raise Exception('Unable to load any plugins')
    except:
      self.log_error('Error: %s', sys.exc_info())
      if fmt == 'json':
        msg, explain = self.responses[404]
        self.error_message_format = json.dumps(
          {'code': 404, 'message': _quote_html(msg), 'explain': explain})
      self.send_error(404)

    return

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
  """ do stuff """

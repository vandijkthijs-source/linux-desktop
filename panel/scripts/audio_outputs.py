"""List and select PipeWire outputs, including inactive ALSA HDMI profiles."""
import json
import subprocess
import time


def run(*args):
    return subprocess.check_output(args, text=True, timeout=4, stderr=subprocess.DEVNULL)


def snapshot():
    return json.loads(run('pw-dump'))


def props(obj):
    return obj.get('info', {}).get('props', {})


def outputs(data):
    default = next((m['value'].get('name') for o in data for m in o.get('metadata', [])
                    if m.get('key') == 'default.audio.sink' and isinstance(m.get('value'), dict)), None)
    sinks = [o for o in data if props(o).get('media.class') == 'Audio/Sink']
    result, handled = [], set()
    for card in data:
        p = props(card)
        if p.get('device.api') != 'alsa' or card.get('type') != 'PipeWire:Interface:Device':
            continue
        params = card.get('info', {}).get('params', {})
        profiles = params.get('EnumProfile', [])
        current = next((x['index'] for x in params.get('Profile', [])), None)
        for route in params.get('EnumRoute', []):
            if route.get('direction') != 'Output':
                continue
            candidates = [x for x in profiles if x['index'] in route.get('profiles', []) and 'output:' in x.get('name', '')]
            if not candidates:
                continue
            # Preserve the microphone by preferring the current or highest-priority duplex profile.
            profile = next((x for x in candidates if x['index'] == current), max(candidates, key=lambda x: x.get('priority', 0)))
            matching = [s for s in sinks if props(s).get('device.id') == card['id'] and props(s).get('card.profile.device') in route.get('devices', [])]
            active_route = any(r.get('direction') == 'Output' and r['index'] == route['index'] for r in params.get('Route', []))
            name = route.get('description', route['name'])
            if route['name'] == 'analog-output-speaker': name = 'Laptopspeakers'
            elif route['name'] == 'analog-output-headphones': name = 'Koptelefoon'
            available = route.get('available') != 'no'
            # Keep the first unplugged HDMI visible to explain when it becomes available.
            if not available and route['name'] != 'hdmi-output-0':
                continue
            result.append(dict(key=f"route:{card['id']}:{route['index']}", label=name,
                               available=available, active=active_route and any(props(s).get('node.name') == default for s in matching),
                               card=card['id'], card_serial=p.get('object.serial'), route=route['index'], profile=profile['index'],
                               devices=route.get('devices', [])))
            handled.update(s['id'] for s in matching)
    for sink in sinks:
        if sink['id'] in handled:
            continue
        p = props(sink)
        result.append(dict(key='sink:'+p['node.name'], label=p.get('node.description', p['node.name']),
                           available=True, active=p['node.name'] == default, sink=p['node.name']))
    return result


def select(choice):
    data = snapshot()
    fresh = next((x for x in outputs(data) if x['key'] == choice['key']), None)
    if not fresh or not fresh['available']:
        raise RuntimeError('Deze uitgang is niet meer beschikbaar.')
    choice = fresh
    if 'card' in choice:
        card = next(o for o in data if o['id'] == choice['card'])
        if props(card).get('object.serial') != choice.get('card_serial'):
            raise RuntimeError('Het audioapparaat is gewijzigd. Kies het opnieuw.')
        current = card['info']['params'].get('Profile', [])
        if not any(p['index'] == choice['profile'] for p in current):
            run('wpctl', 'set-profile', str(choice['card']), str(choice['profile']))
        deadline = time.monotonic() + 3
        while True:
            data = snapshot()
            sink = next((o for o in data if props(o).get('media.class') == 'Audio/Sink'
                         and props(o).get('device.id') == choice['card']
                         and props(o).get('card.profile.device') in choice['devices']), None)
            if sink: break
            if time.monotonic() > deadline: raise RuntimeError('De geluidsuitgang kon niet worden geopend.')
            time.sleep(.1)
        run('wpctl', 'set-route', str(sink['id']), str(choice['route']))
    else:
        sink = next((o for o in data if props(o).get('node.name') == choice['sink']), None)
        if sink is None: raise RuntimeError('De geluidsuitgang is verdwenen.')
    run('wpctl', 'set-default', str(sink['id']))
    for obj in data:
        if props(obj).get('media.class') == 'Stream/Output/Audio':
            run('pw-metadata', '-n', 'default', str(obj['id']), 'target.object', str(props(sink)['object.serial']), 'Spa:Id')
    return sink

"""Dump every Core property path of a fresh node with its type and enum values, for extending the layer compiler."""
import json
from .paths import WORK


def discover():
    from effekseer_ai.session import EffectSession
    s = EffectSession.new()
    from System import Enum  # .NET namespaces import only after EffectSession has loaded Core
    p = 'node/root/0'
    result = {}
    for x in s.property_list(p, 12):
        try:
            o = s._object_at_path(x)
            v = s.property_get(x)
            typ = o.GetType() if hasattr(o, 'GetType') else None
            result[x.removeprefix(p + '/')] = {'value': v, 'type': str(typ)}
            if typ and typ.IsEnum:
                result[x.removeprefix(p + '/')]['enum'] = {str(n): int(Enum.Parse(typ, n)) for n in Enum.GetNames(typ)}
        except Exception as e:
            result[x.removeprefix(p + '/')] = {'error': str(e)}
    path = WORK / 'property_schema.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, default=str))
    return {'ok': True, 'properties': len(result), 'schema': str(path)}

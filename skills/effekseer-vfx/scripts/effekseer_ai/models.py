"""Create Core procedural meshes with validated reflective settings."""
from .runtime import load_core

def model_schema():
 load_core()
 from Effekseer.Data import ProceduralModelParameter
 model=ProceduralModelParameter(); result={}
 def walk(obj,path='',depth=7):
  if not hasattr(obj,'GetType') or depth==0:return
  for member in obj.GetType().GetProperties():
   if not member.CanRead or member.GetIndexParameters().Length or member.Name in {'DefaultValue','Link','IsValueChangedFromDefault'}:continue
   val=getattr(obj,member.Name); p=path+'/'+member.Name if path else member.Name
   if hasattr(val,'GetEnumType'):
    from System import Enum
    result[p]={'value':str(val.Value),'enum':[str(x) for x in Enum.GetNames(val.GetEnumType())]}
   elif hasattr(val,'SetValue') and hasattr(val,'Value'):result[p]={'value':str(val.Value)}
   elif hasattr(val,'GetType') and str(val.GetType().Namespace).startswith('Effekseer'):walk(val,p,depth-1)
 walk(model)
 return result

def assign_procedural_model(session,node_path,properties):
 from Effekseer.Data import ProceduralModelParameter
 model=ProceduralModelParameter(); schema=model_schema()
 for path,value in properties.items():
  if path not in schema:raise ValueError(f'Unknown procedural model property: {path}')
  obj=model
  for member in path.split('/'):obj=getattr(obj,member)
  session._assign_value(obj,value)
 collection=load_core().ProceduralModel.ProceduralModels
 if not collection.Add(model):raise RuntimeError('Procedural model limit reached')
 node=session._node(node_path)
 session._assign_value(node.DrawingValues.Model.ModelReference,'ProceduralModel')
 node.DrawingValues.Model.Reference.SetValue(model)
 return {'node':node_path,'model_index':collection.GetIndex(model),'name':str(model.Name.Value)}

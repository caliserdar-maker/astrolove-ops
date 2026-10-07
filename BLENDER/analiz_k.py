import sys
src=open('/home/claude/blender/analiz.py').read()
src=src.replace("[('REF','/tmp/claude-0/REF/ref.png'),('D2','c_son/SV_BLENDER_2000.jpg'),('D2_beneksiz','c_c60f37/SV_BLENDER_2000.jpg')]",repr([('REF','/tmp/claude-0/REF/ref.png')]+[(d,d+'/SV_BLENDER_2000.jpg') for d in sys.argv[1:]])).replace("analiz.json","analiz_k.json")
exec(src)

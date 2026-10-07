import bpy, numpy as np, sys
for p in sys.argv[sys.argv.index('--')+1:]:
    im=bpy.data.images.load(p); w,h=im.size
    a=np.empty(w*h*4,np.float32); im.pixels.foreach_get(a)
    np.save(p.replace('.exr','.npy'), a.reshape(h,w,4)[::-1].copy())  # ust satir ilk
    print(p, a.reshape(h,w,4)[...,:3].max())

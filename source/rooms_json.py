import json
APTS=[dict(W=11,D=10.5,n=2),dict(W=11,D=10.5,n=2),dict(W=20,D=8.5,n=3)]
BACK={2:[('bed','النوم الرئيسية',.42),('bath','حمام',.16),('bed','غرفة ٢',.42)],
      3:[('bed','النوم الرئيسية',.34),('bath','حمام',.13),('bed','غرفة ٢',.265),('bed','غرفة ٣',.265)]}
PLACE=[lambda x,z:(x,21-z),lambda x,z:(26-x,21-z),lambda x,z:(3+x,z)]
out=[]
for i,A in enumerate(APTS):
    W,D=A['W'],A['D'];zb,xk,zk,xe=D*.42,W*.62,D*.72,W*.8;R=[];x=0
    for t,n,fr in BACK[A['n']]:R.append((n,x,0,x+fr*W,zb));x+=fr*W
    R+=[('الريسيبشن',0,zb,xk,D),('المطبخ',xk,zb,W,zk),('حمام ضيوف',xk,zk,xe,D),('المدخل',xe,zk,W,D)]
    rooms=[]
    for n,x1,z1,x2,z2 in R:
        cx,cz=PLACE[i]((x1+x2)/2,(z1+z2)/2)
        rooms.append(dict(n=n,a=round(abs(x2-x1)*abs(z2-z1),1),d=f'{abs(x2-x1):.2f}×{abs(z2-z1):.2f}',p=[round(cx,2),1.2,round(cz,2)]))
    c=PLACE[i](W/2,D/2)
    out.append(dict(id=i+1,area=round(W*D),beds=A['n'],baths=2,center=[round(c[0],2),0,round(c[1],2)],rooms=rooms))
print(json.dumps(out,ensure_ascii=False))

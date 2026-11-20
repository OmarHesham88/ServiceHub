# Rebuild the typical floor plan from the page's parametric layout
APTS=[dict(k=1,W=11,D=10.5,n=2,opt=dict(back=1,left=1,right=0)),
      dict(k=2,W=11,D=10.5,n=2,opt=dict(back=1,left=1,right=0)),
      dict(k=3,W=20,D=8.5,n=3,opt=dict(back=1,left=1,right=1))]
BACK={2:[('bed','النوم الرئيسية',.42),('bath','حمام',.16),('bed','غرفة ٢',.42)],
      3:[('bed','النوم الرئيسية',.34),('bath','حمام',.13),('bed','غرفة ٢',.265),('bed','غرفة ٣',.265)]}
PLACE=[lambda x,z:(x,21-z), lambda x,z:(26-x,21-z), lambda x,z:(3+x,z)]
S=40; OX=60; OY=60  # px per metre, margins
def P(x,z): return OX+x*S, OY+z*S
walls=[];wins=[];doors=[];rooms=[];labels=[]
def line(L,a,b): L.append((P(*a),P(*b)))
for i,A in enumerate(APTS):
    T=PLACE[i];W,D=A['W'],A['D'];zb=D*.42;xk=W*.62;zk=D*.72;xe=W*.8
    R=[];x=0
    for t,n,fr in BACK[A['n']]: R.append((t,n,x,0,x+fr*W,zb)); x+=fr*W
    R+= [('liv','الريسيبشن',0,zb,xk,D),('kit','المطبخ',xk,zb,W,zk),('bath','حمام ضيوف',xk,zk,xe,D),('ent','المدخل',xe,zk,W,D)]
    def wall(x1,z1,x2,z2,kind=None,g=0):
        hz=z1==z2
        if kind=='door':
            m=((x1+x2)/2,(z1+z2)/2);h=g/2
            a,b=((m[0]-h,z1),(m[0]+h,z1)) if hz else ((x1,m[1]-h),(x1,m[1]+h))
            line(walls,T(x1,z1),T(*a));line(walls,T(*b),T(x2,z2));line(doors,T(*a),T(*b))
        elif kind=='win':
            p=min(.45,((x2-x1) if hz else (z2-z1))/4)
            a,b=((x1+p,z1),(x2-p,z1)) if hz else ((x1,z1+p),(x1,z2-p))
            line(walls,T(x1,z1),T(*a));line(walls,T(*b),T(x2,z2));line(wins,T(*a),T(*b))
        else: line(walls,T(x1,z1),T(x2,z2))
    for t,n,x1,z1,x2,z2 in R:
        if z1==0:
            wall(x1,0,x2,0,'win' if t!='bath' and A['opt']['back'] else None)
            wall(x1,zb,x2,zb,'door',.9)
            if x1>0: wall(x1,0,x1,zb)
    wall(0,D,xk,D);wall(xk,D,xe,D);wall(xe,D,W,D,'door',1.1)
    wall(0,0,0,zb,'win' if A['opt']['left'] else None);wall(0,zb,0,D,'win' if A['opt']['left'] else None)
    wall(W,0,W,zb,'win' if A['opt']['right'] else None);wall(W,zb,W,D)
    wall(xk,zk,xk,D,'door',.8);wall(xk,zk,xe,zk);wall(xe,zk,xe,D)
    for t,n,x1,z1,x2,z2 in R:
        a=P(*T(x1,z1));b=P(*T(x2,z2));rooms.append((t,a,b))
        cx,cz=P(*T((x1+x2)/2,(z1+z2)/2));labels.append((cx,cz,n,f'{abs(x2-x1):.2f} × {abs(z2-z1):.2f} م',t))
    cx,cz=P(*T(W/2,D-1.0)) if i<2 else P(*T(W/2,D-.4))
    labels.append((cx,cz,f'شقة {i+1} — {round(W*D)} م²','', 'apt'))
# core & corridor
for a,b in [((11,10.5),(11,21)),((15,10.5),(15,21)),((11,21),(15,21)),((3,8.5),(3,10.5)),((23,8.5),(23,10.5))]: line(walls,a,b)
line(doors,(11.9,10.5),(14.1,10.5))
labels+= [(*P(13,15.75),'السلم','4.00 × 10.50 م','core'),(*P(13,9.5),'الطرقة','','cor')]
FILL={'bed':'#eef3f6','bath':'#e3eef0','liv':'#f6f1e8','kit':'#f3efe6','ent':'#eeeeea'}
w,h=OX*2+26*S,OY*2+21*S+50
o=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="IBM Plex Sans Arabic,Noto Sans Arabic,sans-serif">',
   f'<rect width="100%" height="100%" fill="#fff"/>']
for t,a,b in rooms:
    o.append(f'<rect x="{min(a[0],b[0])}" y="{min(a[1],b[1])}" width="{abs(b[0]-a[0])}" height="{abs(b[1]-a[1])}" fill="{FILL[t]}"/>')
o.append(f'<rect x="{P(11,0)[0]}" y="{P(0,10.5)[1]}" width="{4*S}" height="{10.5*S}" fill="#e7e4de"/>')
o.append(f'<rect x="{P(3,0)[0]}" y="{P(0,8.5)[1]}" width="{20*S}" height="{2*S}" fill="#ece9e2"/>')
for (a,b) in walls: o.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="#222" stroke-width="6" stroke-linecap="square"/>')
for (a,b) in wins: o.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="#3a8fb7" stroke-width="5"/>')
for cx,cz,n,d,t in labels:
    if t=='apt': o.append(f'<text x="{cx}" y="{cz}" text-anchor="middle" font-size="15" font-weight="700" fill="#14808c">{n}</text>');continue
    o.append(f'<text x="{cx}" y="{cz-2}" text-anchor="middle" font-size="{13 if t!="bath" else 11}" font-weight="600" fill="#222">{n}</text>')
    if d: o.append(f'<text x="{cx}" y="{cz+15}" text-anchor="middle" font-size="11" fill="#666" direction="ltr">{d}</text>')
o.append(f'<text x="{w/2}" y="{h-25}" text-anchor="middle" font-size="18" font-weight="700">مسقط الدور المتكرر — مستخرج من صفحة الجولة (تصوّر تخيلي)</text></svg>')
open('typical-floor.svg','w').write('\n'.join(o))

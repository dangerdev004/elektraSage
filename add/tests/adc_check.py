"""Netlist-level checks for the flash ADC: wires that end on another net, and the encoder's logic for every code."""
from agent.circuits.flash_adc import flash_adc, gate_offsets

def analyse(text):
    lines=text.splitlines()[1:]
    wires=[];gates=[];ms=[];ops=[]
    for l in lines:
        t=l.split()
        if t[0]=='w': wires.append(tuple(map(int,t[1:5])))
        elif t[0] in ('150','151','152','153','154'):
            x1,y1,x2,y2=map(int,t[1:5]); n=int(t[6]); gates.append((x1,y1,x2,y2,n,int(t[0])))
        elif t[0]=='M': ms.append(tuple(map(int,t[1:5])))
        elif t[0]=='a': ops.append(tuple(map(int,t[1:5])))
    return wires,gates,ms,ops

def check_geometry(text):
    wires,gates,_,_=analyse(text)
    bad=0
    # nets by endpoint union
    parent={}
    def f(p):
        parent.setdefault(p,p)
        while parent[p]!=p:
            parent[p]=parent[parent[p]];p=parent[p]
        return p
    for a in wires: parent[f(a[:2])]=f(a[2:])
    def inside(p,w):
        (x1,y1,x2,y2)=w
        if x1==x2==p[0] and min(y1,y2)<p[1]<max(y1,y2): return True
        if y1==y2==p[1] and min(x1,x2)<p[0]<max(x1,x2): return True
        return False
    ends=set()
    for w in wires: ends.add(w[:2]);ends.add(w[2:])
    for (x1,y1,x2,y2,n,_) in gates:
        for o in gate_offsets(n): ends.add((x1,y1-16*o))
        ends.add((x2,y2))
    for p in ends:
        for w in wires:
            if inside(p,w) and f(p)!=f(w[:2]):
                bad+=1
    return bad

def check_logic(text, bits):
    wires,gates,ms,ops=analyse(text)
    m=2**bits
    parent={}
    def f(p):
        parent.setdefault(p,p)
        while parent[p]!=p:
            parent[p]=parent[parent[p]];p=parent[p]
        return p
    for a in wires: parent[f(a[:2])]=f(a[2:])
    # comparators: output pin (x2,y2); threshold index k = m - j with y2 = 80+48j-16
    comp={}
    for (x1,y1,x2,y2) in ops:
        j=(y2+16-80)//48; comp[f((x2,y2))]=m-j
    gate_in=[];gate_out=[]
    for (x1,y1,x2,y2,n,kind) in gates:
        gate_in.append([f((x1,y1-16*o)) for o in gate_offsets(n)]); gate_out.append(f((x2,y2)))
    mnet=[f((x1,y1)) for (x1,y1,x2,y2) in ms]
    ok=True
    for code in range(m):
        val={}
        for net,k in comp.items(): val[net]=1 if code>=k else 0
        # evaluate gates until stable
        changed=True; it=0
        while changed and it<1000:
            changed=False; it+=1
            for ins,out in zip(gate_in,gate_out):
                if all(i in val for i in ins):
                    v=sum(val[i] for i in ins)%2
                    if val.get(out)!=v: val[out]=v; changed=True
        got=0
        # M outputs: sorted by row: need mapping to bit; use known structure -> collect values by M, decode by trying order
        vals=[val.get(n) for n in mnet]
        if None in vals: return False, f"unresolved M at code {code}"
        got=sorted(vals)  # placeholder
        # decode: M nets order is by bit: chains emitted from bit n-2 down to 0, then top bit last
        order=list(range(bits-2,-1,-1))+[bits-1]
        word=sum(v<<b for v,b in zip(vals,order))
        if word!=code: ok=False; return False,(code,word,vals)
    return True,'ok'


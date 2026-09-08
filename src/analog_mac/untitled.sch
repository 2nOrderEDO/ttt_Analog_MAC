v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 240 160 240 200 {lab=0}
N 240 80 240 100 {lab=#net1}
N 90 50 100 50 {lab=0}
N 90 50 90 80 {lab=0}
N 90 80 100 80 {lab=0}
N 240 50 250 50 {lab=#net1}
N 250 50 250 80 {lab=#net1}
N 240 80 250 80 {lab=#net1}
N 100 80 100 200 {lab=0}
N 140 50 160 50 {lab=#net2}
N 160 0 160 50 {lab=#net2}
N 100 0 160 0 {lab=#net2}
N 100 0 100 20 {lab=#net2}
N 160 50 200 50 {lab=#net2}
N 30 -20 30 0 {lab=0}
N 30 -90 30 -80 {lab=#net3}
N 30 -90 100 -90 {lab=#net3}
N 240 -90 240 20 {lab=#net3}
N 100 -90 240 -90 {lab=#net3}
N 100 -20 100 -0 {lab=#net2}
N 100 -90 100 -80 {lab=#net3}
C {sky130_fd_pr/nfet_01v8.sym} 120 50 0 1 {name=M1
W=1
L=0.15
nf=1 
mult=1
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/nfet_01v8.sym} 220 50 0 0 {name=M2
W=1
L=0.15
nf=1 
mult=1
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {vsource.sym} 240 130 0 0 {name=V1 value=0 savecurrent=false}
C {gnd.sym} 240 200 0 0 {name=l1 lab=0}
C {gnd.sym} 100 200 0 0 {name=l2 lab=0}
C {vsource.sym} 30 -50 0 0 {name=V2 value=1.8 savecurrent=false}
C {gnd.sym} 30 0 0 0 {name=l3 lab=0}
C {isource.sym} 100 -50 0 0 {name=I0 value=1m}

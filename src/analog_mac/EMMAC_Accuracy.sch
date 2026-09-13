v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
B 2 10 -1390 810 -770 {flags=graph
y1=-1.660178e-05
y2=1.7678647e-05
ypos1=0
ypos2=2
divy=5
subdivy=1
unity=1
x1=0.00055844628
x2=0.0025584465
divx=5
subdivx=1
xlabmag=1.0
ylabmag=1.0
legendmag=1.0
node="i(v2)
i(V0)"
color="4 7"
dataset=-1
unitx=1
logx=0
logy=0
autoload=1
sim_type=tran
rawfile=$netlist_dir/EMMAC_UnitTest_tran.raw}
N -160 130 -160 140 {lab=0}
N -500 130 -500 140 {lab=#net1}
N -500 10 -500 70 {lab=#net2}
N -160 -10 -160 70 {lab=#net3}
N 210 -10 210 70 {lab=#net4}
N 210 130 210 140 {lab=0}
N -160 -10 -140 -10 {lab=#net3}
N -500 200 -500 210 {lab=0}
N -500 10 -140 10 {lab=#net2}
N 160 -10 210 -10 {lab=#net4}
C {vsource.sym} -160 100 0 0 {name=V1 value=1.8 savecurrent=false}
C {isource.sym} -500 100 2 0 {name=I0 value=0 savecurrent=false}
C {vsource.sym} 210 100 0 0 {name=V2 value=0.5 savecurrent=false}
C {gnd.sym} 210 140 0 0 {name=l1 lab=0}
C {gnd.sym} -500 210 0 0 {name=l2 lab=0}
C {gnd.sym} -160 140 0 0 {name=l3 lab=0}
C {devices/code_shown.sym} 300 -60 0 0 {name=MODEL only_toplevel=true
format="tcleval( @value )"
value=".lib cornerMOSlv.lib mos_tt
.lib cornerMOShv.lib mos_tt
"}
C {code_shown.sym} 300 40 0 0 {name=spice1 only_toplevel=false value="
.control
	option savecurrents
	set noaskquit
	set filetype=ascii
	op
	print v(net2) i(v2)
.endc

.save all
"}
C {launcher.sym} 60 -710 0 0 {name=h5
descr="load waves"
tclcommand="xschem raw_read $netlist_dir/accuracy/acc_k1_i0.raw dc"
}
C {vsource.sym} -500 170 0 0 {name=V0 value=0 savecurrent=false}
C {EMMAC_Block_v2.sym} 10 0 0 0 {name=x2 wmul=1}

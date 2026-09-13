v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
B 2 0 -570 800 -170 {flags=graph
y1=-2e-06
y2=2e-06
ypos1=0
ypos2=2
divy=5
subdivy=1
unity=1
x1=0
x2=0.002
divx=5
subdivx=1
xlabmag=1.0
ylabmag=1.0
legendmag=1.0
node="i(v2)
i(v.x1.v0)"
color="4 12"
dataset=-1
unitx=1
logx=0
logy=0
autoload=1
sim_type=tran
rawfile=$netlist_dir/EMMAC_UnitTest_tran.raw}
N -400 130 -400 140 {lab=0}
N -190 130 -190 140 {lab=0}
N -190 10 -190 70 {lab=#net1}
N -190 10 -140 10 {lab=#net1}
N -400 -10 -400 70 {lab=#net2}
N 210 -10 210 70 {lab=#net3}
N 160 -10 210 -10 {lab=#net3}
N 210 130 210 140 {lab=0}
N -400 -10 -140 -10 {lab=#net2}
C {EMMAC_Block.sym} 10 0 0 0 {name=x1 W=2}
C {vsource.sym} -400 100 0 0 {name=V1 value=1.8 savecurrent=false}
C {isource.sym} -190 100 2 0 {name=I0 value="PULSE 2u -2u 1m 1u 1u 1"}
C {vsource.sym} 210 100 0 0 {name=V2 value=0.5 savecurrent=false}
C {gnd.sym} 210 140 0 0 {name=l1 lab=0}
C {gnd.sym} -190 140 0 0 {name=l2 lab=0}
C {gnd.sym} -400 140 0 0 {name=l3 lab=0}
C {devices/code_shown.sym} 300 -60 0 0 {name=MODEL only_toplevel=true
format="tcleval( @value )"
value=".lib cornerMOSlv.lib mos_tt
.lib cornerMOShv.lib mos_tt
"}
C {code_shown.sym} 300 40 0 0 {name=spice1 only_toplevel=false value="
.control
	option savecurrents
	op
	print all
	write EMMAC_UnitTest.raw
	reset
	tran 10u 2m
	write EMMAC_UnitTest_tran.raw
.endc

.save all
"}
C {launcher.sym} 60 -140 0 0 {name=h5
descr="load waves"
tclcommand="xschem raw_read $netlist_dir/EMMAC_UnitTest_tran.raw tran"
}

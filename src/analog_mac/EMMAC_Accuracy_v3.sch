v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
B 2 10 -850 810 -230 {flags=graph
y1=-5.7e-05
y2=5.6e-05
ypos1=0
ypos2=2
divy=5
subdivy=1
unity=1
x1=-8e-06
x2=7e-06
divx=5
subdivx=1
xlabmag=1.0
ylabmag=1.0
legendmag=1.0
node="i(Vout)
i(Videal)"
color="4 7"
dataset=-1
unitx=1
logx=0
logy=0
autoload=1
sim_type=table
hilight_wave=1}
N -160 130 -160 140 {lab=GND}
N -500 130 -500 140 {lab=#net1}
N -500 10 -500 70 {lab=#net2}
N -160 -10 -160 70 {lab=#net3}
N 330 130 330 140 {lab=GND}
N -160 -10 -140 -10 {lab=#net3}
N -500 200 -500 210 {lab=GND}
N -500 10 -140 10 {lab=#net2}
N 160 -10 210 -10 {lab=#net4}
N 330 -10 330 70 {lab=#net5}
N 270 -10 330 -10 {lab=#net5}
N 510 -10 510 10 {lab=GND}
N 430 -10 510 -10 {lab=GND}
N 430 -10 430 -0 {lab=GND}
N 430 130 430 140 {lab=GND}
N 430 60 430 70 {lab=#net6}
C {vsource.sym} -160 100 0 0 {name=V1 value=1.5 savecurrent=false}
C {isource.sym} -500 100 2 0 {name=Iin value=0 savecurrent=false}
C {vsource.sym} 330 100 0 0 {name=Vout value=0.5 savecurrent=false}
C {gnd.sym} 330 140 0 0 {name=l1 lab=GND}
C {gnd.sym} -500 210 0 0 {name=l2 lab=GND}
C {gnd.sym} -160 140 0 0 {name=l3 lab=GND}
C {devices/code_shown.sym} 690 -60 0 0 {name=MODEL only_toplevel=true
format="tcleval( @value )"
value=".lib cornerMOSlv.lib mos_tt
.lib cornerMOShv.lib mos_tt
.lib cornerRES.lib res_typ_stat
"}
C {code_shown.sym} 680 40 0 0 {name=spice1 only_toplevel=false value="
.control
	option savecurrents
	save all
	op
	write EMMAC_Accuracy_v3_op.raw
	dc Iin -8u 7u 1u
	print v(net2) i(Vout)
	write EMMAC_Accuracy_v3_sweep.raw
.endc
"}
C {launcher.sym} 60 -170 0 0 {name=h5
descr="load waves"
tclcommand="xschem raw_read $netlist_dir/EMMAC_Accuracy_v3_sweep.raw"
}
C {vsource.sym} -500 170 0 0 {name=V0 value=0 savecurrent=false}
C {EMMAC_Block_v3.sym} 10 0 0 0 {name=x2 wmul=7}
C {vsource.sym} 240 -10 3 0 {name=V4 value=0 savecurrent=false}
C {cccs.sym} 430 30 0 0 {name=F1 vnam=V0 value=-7}
C {gnd.sym} 430 140 0 0 {name=l4 lab=GND}
C {gnd.sym} 510 10 0 0 {name=l5 lab=GND}
C {vsource.sym} 430 100 0 0 {name=Videal value=0.5 savecurrent=false}

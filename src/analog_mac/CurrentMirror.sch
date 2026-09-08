v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
B 2 0 430 520 820 {flags=graph
y1=4e-06
y2=6.1e-06
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
node=i(v1)
color=4
dataset=-1
unitx=1
logx=0
logy=0
hilight_wave=-1
autoload=1
rawfile=$netlist_dir/CurrentMirror_tran.raw
sim_type=tran}
N 0 -60 0 -50 {lab=#net1}
N 140 -60 280 -60 {lab=#net1}
N 140 -60 140 -50 {lab=#net1}
N 280 -60 280 -50 {lab=#net1}
N 280 360 280 380 {lab=0}
N 140 360 140 380 {lab=0}
N 220 320 240 320 {lab=Out}
N 130 320 140 320 {lab=0}
N 130 320 130 360 {lab=0}
N 130 360 140 360 {lab=0}
N 280 320 290 320 {lab=0}
N 290 320 290 360 {lab=0}
N 280 360 290 360 {lab=0}
N 140 350 140 360 {lab=0}
N 280 350 280 360 {lab=0}
N 280 100 370 100 {lab=0}
N 140 170 140 290 {lab=In}
N 40 140 140 140 {lab=0}
N 180 140 200 140 {lab=#net2}
N 200 100 200 140 {lab=#net2}
N 0 10 0 40 {lab=0}
N 140 10 140 30 {lab=#net3}
N 140 100 140 110 {lab=#net2}
N 140 100 200 100 {lab=#net2}
N 140 90 140 100 {lab=#net2}
N 200 100 240 100 {lab=#net2}
N 280 250 280 290 {lab=Out}
N 280 10 280 70 {lab=#net4}
N 0 -60 140 -60 {lab=#net1}
N 220 250 220 320 {lab=Out}
N 180 320 220 320 {lab=Out}
N 220 250 280 250 {lab=Out}
N 280 130 280 250 {lab=Out}
C {vsource.sym} 280 -20 0 0 {name=V1 value=0 savecurrent=false}
C {gnd.sym} 280 380 0 0 {name=l1 lab=0}
C {gnd.sym} 140 380 0 0 {name=l2 lab=0}
C {vsource.sym} 0 -20 0 0 {name=V2 value=3 savecurrent=false}
C {gnd.sym} 0 40 0 0 {name=l3 lab=0}
C {isource.sym} 140 -20 0 0 {name=I0 value="PULSE 2u 3u 1m 1u 1u 1"}
C {lab_pin.sym} 280 270 0 0 {name=p1 sig_type=std_logic lab=Out}
C {lab_pin.sym} 140 270 0 0 {name=p2 sig_type=std_logic lab=In}
C {sg13g2_pr/sg13_lv_nmos.sym} 160 320 0 1 {name=M1
l=1u
w=0.15u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13g2_pr/sg13_lv_nmos.sym} 260 320 0 0 {name=M2
l=1u
w=0.15u
ng=1
m=2
model=sg13_lv_nmos
spiceprefix=X
}
C {devices/code_shown.sym} 400 70 0 0 {name=MODEL only_toplevel=true
format="tcleval( @value )"
value=".lib cornerMOSlv.lib mos_tt
"}
C {code_shown.sym} 400 140 0 0 {name=spice1 only_toplevel=false value="
.control
	option savecurrents
	op
	print all
	write CurrentMirror.raw
	reset
	tran 10u 2m
	write CurrentMirror_tran.raw
.endc

.save all
"}
C {vsource.sym} 140 60 0 0 {name=V3 value=0 savecurrent=false}
C {sg13g2_pr/sg13_lv_nmos.sym} 260 100 0 0 {name=M3
l=1u
w=0.15u
ng=1
m=2
model=sg13_lv_nmos
spiceprefix=X
}
C {gnd.sym} 370 100 0 0 {name=l4 lab=0}
C {sg13g2_pr/sg13_lv_nmos.sym} 160 140 0 1 {name=M4
l=1u
w=0.15u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {gnd.sym} 40 140 0 0 {name=l5 lab=0}
C {sg13g2_pr/annotate_fet_params.sym} 380 -190 0 0 {name=annot1 ref=M1}
C {launcher.sym} 70 860 0 0 {name=h5
descr="load waves"
tclcommand="xschem raw_read $netlist_dir/CurrentMirror_tran.raw tran"
}

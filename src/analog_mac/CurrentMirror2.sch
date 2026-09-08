v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
B 2 0 530 520 920 {flags=graph
y1=4.7e-06
y2=6.9e-06
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
N 140 -60 140 -50 {lab=#net1}
N 280 -60 280 80 {lab=#net1}
N 280 470 280 490 {lab=0}
N 140 470 140 490 {lab=0}
N 130 430 140 430 {lab=0}
N 130 430 130 470 {lab=0}
N 130 470 140 470 {lab=0}
N 280 430 290 430 {lab=0}
N 290 430 290 470 {lab=0}
N 280 470 290 470 {lab=0}
N 140 460 140 470 {lab=0}
N 280 460 280 470 {lab=0}
N 0 10 0 40 {lab=0}
N 140 10 140 30 {lab=#net2}
N 0 -60 140 -60 {lab=#net1}
N 330 120 410 120 {lab=#net3}
N 140 -60 280 -60 {lab=#net1}
N 280 80 280 90 {lab=#net1}
N 450 80 450 90 {lab=#net1}
N 280 -60 450 -60 {lab=#net1}
N 270 120 280 120 {lab=#net1}
N 270 80 270 120 {lab=#net1}
N 270 80 280 80 {lab=#net1}
N 450 120 460 120 {lab=#net1}
N 460 80 460 120 {lab=#net1}
N 450 80 460 80 {lab=#net1}
N 450 -60 450 80 {lab=#net1}
N 220 430 240 430 {lab=Out}
N 280 150 280 160 {lab=#net3}
N 330 120 330 160 {lab=#net3}
N 320 120 330 120 {lab=#net3}
N 280 160 330 160 {lab=#net3}
N 280 160 280 180 {lab=#net3}
N 280 380 280 400 {lab=Out}
N 280 330 290 330 {lab=Out}
N 290 330 290 370 {lab=Out}
N 280 370 290 370 {lab=Out}
N 280 360 280 370 {lab=Out}
N 200 330 240 330 {lab=A1}
N 140 370 140 400 {lab=In}
N 180 430 220 430 {lab=Out}
N 220 380 280 380 {lab=Out}
N 280 370 280 380 {lab=Out}
N 220 380 220 430 {lab=Out}
N 140 280 140 300 {lab=A1}
N 180 330 200 330 {lab=A1}
N 200 280 200 330 {lab=A1}
N 140 280 200 280 {lab=A1}
N 140 90 140 280 {lab=A1}
N 280 240 280 300 {lab=#net4}
N 130 330 140 330 {lab=In}
N 130 330 130 370 {lab=In}
N 130 370 140 370 {lab=In}
N 140 360 140 370 {lab=In}
N 450 150 450 180 {lab=#net5}
N 590 470 590 490 {lab=0}
N 450 470 450 490 {lab=0}
N 440 430 450 430 {lab=0}
N 440 430 440 470 {lab=0}
N 440 470 450 470 {lab=0}
N 590 430 600 430 {lab=0}
N 600 430 600 470 {lab=0}
N 590 470 600 470 {lab=0}
N 450 460 450 470 {lab=0}
N 590 460 590 470 {lab=0}
N 530 430 550 430 {lab=#net6}
N 590 380 590 400 {lab=#net6}
N 590 330 600 330 {lab=#net6}
N 600 330 600 370 {lab=#net6}
N 590 370 600 370 {lab=#net6}
N 590 360 590 370 {lab=#net6}
N 510 330 550 330 {lab=#net7}
N 450 370 450 400 {lab=#net8}
N 490 430 530 430 {lab=#net6}
N 530 380 590 380 {lab=#net6}
N 590 370 590 380 {lab=#net6}
N 530 380 530 430 {lab=#net6}
N 450 280 450 300 {lab=#net7}
N 490 330 510 330 {lab=#net7}
N 510 280 510 330 {lab=#net7}
N 450 280 510 280 {lab=#net7}
N 440 330 450 330 {lab=#net8}
N 440 330 440 370 {lab=#net8}
N 440 370 450 370 {lab=#net8}
N 450 360 450 370 {lab=#net8}
N 450 240 450 280 {lab=#net7}
N 590 240 590 300 {lab=#net9}
N 590 -60 590 180 {lab=#net1}
N 450 -60 590 -60 {lab=#net1}
C {vsource.sym} 280 210 0 0 {name=V1 value=0 savecurrent=false}
C {gnd.sym} 280 490 0 0 {name=l1 lab=0}
C {gnd.sym} 140 490 0 0 {name=l2 lab=0}
C {vsource.sym} 0 -20 0 0 {name=V2 value=1.8 savecurrent=false}
C {gnd.sym} 0 40 0 0 {name=l3 lab=0}
C {isource.sym} 140 -20 0 0 {name=I0 value="PULSE 1u 2u 1m 1u 1u 1"}
C {lab_pin.sym} 220 380 0 0 {name=p1 sig_type=std_logic lab=Out}
C {lab_pin.sym} 140 380 0 0 {name=p2 sig_type=std_logic lab=In}
C {sg13g2_pr/sg13_lv_nmos.sym} 160 430 0 1 {name=M1
l=1u
w=0.15u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13g2_pr/sg13_lv_nmos.sym} 260 430 0 0 {name=M2
l=1u
w=0.15u
ng=1
m=2
model=sg13_lv_nmos
spiceprefix=X
}
C {devices/code_shown.sym} 630 -110 0 0 {name=MODEL only_toplevel=true
format="tcleval( @value )"
value=".lib cornerMOSlv.lib mos_tt
"}
C {code_shown.sym} 1030 -420 0 0 {name=spice1 only_toplevel=false value="
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
C {launcher.sym} 70 860 0 0 {name=h5
descr="load waves"
tclcommand="xschem raw_read $netlist_dir/CurrentMirror_tran.raw tran"
}
C {sg13g2_pr/sg13_lv_pmos.sym} 300 120 0 1 {name=M3
l=1u
w=0.15u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
C {sg13g2_pr/sg13_lv_pmos.sym} 430 120 0 0 {name=M4
l=1u
w=0.15u
ng=1
m=2
model=sg13_lv_pmos
spiceprefix=X
}
C {vsource.sym} 450 210 0 0 {name=V4 value=0 savecurrent=false}
C {sg13g2_pr/sg13_lv_nmos.sym} 160 330 0 1 {name=M5
l=1u
w=0.15u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13g2_pr/sg13_lv_nmos.sym} 260 330 0 0 {name=M6
l=1u
w=0.15u
ng=1
m=2
model=sg13_lv_nmos
spiceprefix=X
}
C {lab_pin.sym} 140 200 0 0 {name=p3 sig_type=std_logic lab=A1}
C {gnd.sym} 590 490 0 0 {name=l4 lab=0}
C {gnd.sym} 450 490 0 0 {name=l5 lab=0}
C {sg13g2_pr/sg13_lv_nmos.sym} 470 430 0 1 {name=M7
l=1u
w=0.15u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13g2_pr/sg13_lv_nmos.sym} 570 430 0 0 {name=M8
l=1u
w=0.15u
ng=1
m=2
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13g2_pr/sg13_lv_nmos.sym} 470 330 0 1 {name=M9
l=1u
w=0.15u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13g2_pr/sg13_lv_nmos.sym} 570 330 0 0 {name=M10
l=1u
w=0.15u
ng=1
m=2
model=sg13_lv_nmos
spiceprefix=X
}
C {vsource.sym} 590 210 0 0 {name=V5 value=0 savecurrent=false}

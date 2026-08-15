set pagination off
set confirm off
set architecture i386
target remote localhost:12345

# MID2PianoCD v1.22 : CMid2Disklavier est dans ECX à l'entrée de 0x4042c0.
# Les 16 modèles commencent à this+0x2d8 et font chacun 0x1180 octets.
set $templates_dumped = 0
break *0x004042c0
commands
  silent
  set $template_this = $ecx
  if $templates_dumped == 0
    printf "template_this=%08x\n", $template_this
    dump binary memory yamaha_templates.bin $template_this+0x2d8 $template_this+0x120d8
    set $templates_dumped = 1
    printf "templates dumped: 16 x 0x1180 bytes\n"
    disable 1
    detach
    quit
  end
  continue
end
continue
set logging enabled off
detach
quit

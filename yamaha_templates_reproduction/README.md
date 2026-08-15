# Reproduction de `yamaha_templates.bin`

Ce dossier conserve les éléments ayant servi à extraire le fichier
`yamaha_templates.bin` depuis la mémoire de `MID2PianoCD v1.22` :

- `dump_mid2pianocd_templates.sh` : attache GDB au processus Wine ;
- `dump_mid2pianocd_templates.gdb` : intercepte l'initialisation et extrait
  les modèles audio ;
- `test.mid` : petit fichier MIDI utilisé pour déclencher une conversion ;
- `MID2PianoCD_v1.22_setup.exe` : installeur du programme observé, conservé
  comme dépendance de reproduction ;
- `yamaha_templates.bin` : résultat extrait, également utilisé par le
  convertisseur.

## Méthode

1. Installer et lancer `MID2PianoCD v1.22` sous Wine.
2. Repérer le PID Wine du programme.
3. Lancer une conversion de `test.mid` dans MID2PianoCD.
4. Depuis ce dossier, exécuter :

   ```bash
   chmod +x dump_mid2pianocd_templates.sh
   ./dump_mid2pianocd_templates.sh <PID_WINE>
   ```

   Le second argument facultatif permet de changer le port GDB :
   `./dump_mid2pianocd_templates.sh <PID_WINE> 12346`.

Le script s'arrête au point `0x004042c0`, récupère le pointeur `CMid2Disklavier`
dans `ECX`, puis copie la zone `this+0x2d8` à `this+0x120d8`. Cette zone
contient 16 modèles de 0x1180 octets, soit 2 240 échantillons PCM signés
16 bits little-endian par modèle : 16 × 2 240 × 2 = 71 680 octets.

## Vérification

Le fichier obtenu doit faire 71 680 octets. L'exemplaire fourni ici a le
SHA-256 suivant :

```text
99c60627aa7fe8932b51a60da953c8cad9f8a1ab9d1aac8902c5976c53780046
```

## Limites

Les adresses et offsets du script correspondent à `MID2PianoCD v1.22` et à
l'exécutable observé. Une autre version peut nécessiter une nouvelle analyse
dans GDB. La procédure nécessite Wine, `winedbg` et GDB ; l'installeur est
fourni uniquement pour conserver la dépendance locale ayant servi à la
capture.

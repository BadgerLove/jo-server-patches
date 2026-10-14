"""Keep claymores after a respawn (server).  A player's claymores stay armed when they die and redeploy.

Stock: every claymore, AT mine and satchel a player placed is removed the
moment they redeploy.  With this patch claymores stay in the world and still
go off.  AT mines and satchels are unchanged (patch 20 keeps AT mines), and a
player who LEAVES the server still takes all their devices with them.

Changes (all asserted before writing):
  site VA 0x546E8B  cmp edx,[claymore ammo def]  -> jmp cave / nop
  cave VA 0x7BFF00  (31 B in the zero tail of `_text`)
  PE   `_text` VirtualSize 0x2AA10 -> 0x2B000, if patch 14/15 has not done it

Only the server needs it (the host removes devices and tells every player);
clients need nothing.  The 4-claymore limit per player is unchanged.

Usage:  python patch_keep_claymores.py <in_server.exe> <out.exe>
"""
from keep_devices import main

if __name__ == "__main__":
    main("claymore", __doc__)

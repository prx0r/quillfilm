#!/bin/bash
# Build every quill pack for the gochema video queue. Repeatable: re-run any
# time an essay changes. Manifest titles/blurbs are preserved across runs.
set -e
D=/root/manuscriptAI/deploy
G=/root/gochema/essays
GR=$G/global-rebirth

mk() { python3 $D/make-pack.py "$1" "$2" --title "$3" --blurb "$4"; }

# 0. Rebirth (already live — rebuild picks up v1.2+ edits)
mk rebirth $G/rebirth-explained \
  "Buddhist Reincarnation, Actually Explained" \
  "30-min magnum cut: v1.2 script, storyboard, draft1 + WEAVE quote bank, 13 school resources, sutta extracts."

# 1. Prayer (new)
mk prayer $G/prayer-explained \
  "What Actually Happens When You Pray" \
  "NEW — scaffold v0.1: tour of takes (nembutsu + Saiva japa banked, 6 stops to acquire). Structure + WEAVE + acquire list."

# 1b. Karma (new — owner brief verbatim in draft1)
mk karma $G/karma-explained \
  "Why Karma Governs Your Life" \
  "NEW — owner brief locked: unfairness-first, rebirth-domino, habits bridge, fractal ladder, practice. 8 quote extracts banked."

# 2. The 13 tradition films (+ shared frame/close, global weave, visuals)
declare -A RES=( [hindu]=01-hindu [zoroastrian]=04-zoroastrian [egyptian]=05-egyptian
  [jewish]=06-jewish [gnostic]=07-gnostic-origen [orthodox-christian]=08-orthodox-christian
  [greek]=03-greek [jain]=02-jain [daoist]=09-daoist [yoruba]=10-yoruba
  [saiva]=11-saiva [channeled]=12-channeled [astral-archons]=13-astral-archons )
declare -A TITLE=( [hindu]="Change of Clothes" [zoroastrian]="The Bridge That Narrows"
  [egyptian]="Heart Against a Feather" [jewish]="A Hair From Dough"
  [gnostic]="Light Wearing Meat" [orthodox-christian]="In the Twinkling of an Eye"
  [greek]="Practising Dying" [jain]="The Dust That Sticks" [daoist]="Death by Appointment"
  [yoruba]="You Chose Your Head" [saiva]="Recognition, Not Rebirth"
  [channeled]="All Your Lives Are Now" [astral-archons]="The Toll Booth" )
declare -A DIR=( [hindu]=01-hindu [zoroastrian]=02-zoroastrian [egyptian]=03-egyptian
  [jewish]=04-jewish [gnostic]=05-gnostic [orthodox-christian]=06-orthodox-christian
  [greek]=07-greek [jain]=08-jain [daoist]=09-daoist [yoruba]=10-yoruba
  [saiva]=11-saiva [channeled]=12-channeled [astral-archons]=13-astral-archons )
for f in hindu zoroastrian egyptian jewish gnostic orthodox-christian greek jain daoist yoruba saiva channeled astral-archons; do
  mk "film-$f" $GR/films/${DIR[$f]} "${TITLE[$f]}" "Tradition film: core + movie spec with beats, cinematography, READ list."
done
# shared canon into every film pack
for f in hindu zoroastrian egyptian jewish gnostic orthodox-christian greek jain daoist yoruba saiva channeled astral-archons; do
  S=/root/manuscriptAI/public/packs/film-$f/sources
  cp $GR/films/_shared/FRAME.md $GR/films/_shared/CLOSE.md $S/
  cp $GR/WEAVE-GLOBAL.md $GR/ONTOLOGY.md $GR/TITLES.md $GR/STRUCTURE.md $S/ 2>/dev/null || true
  cp $GR/resources/${RES[$f]}.md $S/ 2>/dev/null || true
  cp /root/gochema/CINEMA.md /root/gochema/VISUAL-GRAMMAR.md $S/ 2>/dev/null || true
done

# 3. Specials
mk special-enter-another-body $GR/films/specials/enter-another-body \
  "Enter Another Body At Will (special)" \
  "Voluntary transfer across 8 traditions: Saiva paradehapravesa + ibbur/dybbuk + phowa + Varanasi."
mk special-gateway $GR/films/specials/gateway \
  "How to Leave Your Body (gateway special)" \
  "Lineage canon: filter to Bergson to Monroe to Campbell + Saiva/Tibetan metaphysics verdict."

# 4. Standalone essays with real content
mk daimon $G/daimon-companion \
  "Daimon Companion (seed film)" \
  "Source essay + 102-shot storyboard + narration + alignment/integrity reports from the volume build."
mk fire-simile $G/fire-simile \
  "Fire Simile" \
  "v1 reading + v2 analysis + source texts. The extinction-mechanism film."
mk dependent-origination $G/dependent-origination \
  "Dependent Origination" \
  "Source + structure. The engine room film (v2 spine)."
mk fundamental-structure $G/fundamental-structure \
  "Fundamental Structure (Nanavira)" \
  "fs extracts + structure + video spec. Time-doctrine material for the rebirth ch.9."

# 5. Manifest regen (picks up the post-copied shared files)
python3 $D/make-pack.py --manifest-only
echo "=== packs ==="
python3 -c "import json; [print('-',p['slug'],'|',p['title'],'|',len(p['manuscripts']),'md,',len(p['sources']),'src') for p in json.load(open('/root/manuscriptAI/public/packs/packs.json'))['packs']]"

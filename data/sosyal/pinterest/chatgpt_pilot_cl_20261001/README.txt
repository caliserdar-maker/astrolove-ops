ASTROLOVEART PINTEREST PILOT | 1 OCTOBER 2026 | FRAME REVISION V2

Start with AstroLove_Pinterest_Research_Design.pdf and Pinterest_Pin_Preview.jpg.
Upload-ready JPG/PNG pins: pins/. Profile cover: profile/.
This package contains four 1000x1500 image Pins and one 1600x900 profile cover.

SOURCE STATUS
The framed artwork uses the genuine reference uploaded by the user on
October 1, 2026. The full frame, symbol, names and message are retained.
Source: sources/frame_reference.jpg, 1588x1191. Exact frame crop:
[left, top, right, bottom] = [354, 40, 1236, 1151], size 882x1111.
Pins 01, 02, 04 and the profile cover use this reference.
The five unframed color artworks use the existing real Drive gallery snapshot
dated September 27, 2026. These are not verified October 1 live listing reads.
See source_provenance.json for source URLs, source sizes, hashes and crop boxes.

LAYERS
assets/scene_empty_master.png: new EMPTY scene, no poster, frame or artwork.
assets/scene_empty_1000x1500.png: pin-sized empty scene.
assets/bg_cream_1000x1500.png: empty cream background for pins 02 and 03.
assets/bg_gift_1000x1500.png: empty reusable background for pin 04.
assets/bg_cream_1600x900.png: empty profile cover background.
assets/real_*.png: exact source product crops; no edits inside the artwork.
layers/: one full-canvas PNG per layer, in bottom-to-top order.
layer_manifest.json: every layer, source path, source hash, pixel rectangle,
text content, x/y anchor, font file, font pixels, font points and hex color.
layer_list.csv: the same placement information in tabular form.
templates/: linked SVG assembly files, using the layer PNGs. They have no
editable text objects. Preserve the package folder structure when opening them.
The Python configuration and JSON are the editable source of the layout.

COORDINATES AND POINTS
Origin: top-left. x points right, y points down.
Rectangles: [x, y, width, height]. Source crops: [left, top, right, bottom].
Typography is defined in pixels at 96 dpi. Points = pixels * 0.75.
The fonts affect only the new surrounding copy, never the product text.

REPRODUCE
Requires Python 3 and Pillow. Run from this folder:
python build_pins.py --config pair.json

FOR OTHER PAIRS
Create a JSON with pair_display, framed_artwork, colors and target_url.
Supply existing real product assets. The five colors array contains label
and asset for each color. Assets are paths relative to this package.
python build_pins.py --config pairs/aries_leo.json --prefix Aries_Leo

Use a unique --prefix for every pair. Output filenames, layer directories,
SVGs, manifest, layer CSV and QA files all include that prefix.
Do not rerun the default empty prefix for multiple pairs in one folder.
Use full-resolution original poster files for the 78-pair production run.
Uniform resize + contain preserve aspect ratio. No redraw, retouch, recolor,
stretch, rotation or perspective transformation is performed.

PIN TEXT
pin_copy.csv supplies proposed titles, descriptions, destination URL,
suggested board, alt text and a background-AI flag. No pins were published.
For pins 01 and 04, mark that the scene was made partly with AI in Pinterest.
The real product was inserted separately after background generation.
The original provenance of the existing poster files is not asserted here.

QA
qa_results.json records product placement comparisons.
Mathematical pixel matching uses PNG, not compressed JPG exports.

BACKGROUND GENERATION
The built-in image generation tool produced only the empty scene.
scene_prompt.txt contains the prompt. No product image was sent to generation.
Font files and the original font license are in fonts/.

RESEARCH LIMIT
The PDF links official Pinterest rules, Etsy sellers and indexed pin examples.
Direct Pinterest examples could not be visually inspected due to access errors.
Seller Etsy success, pin publisher identity and pin performance are separate.

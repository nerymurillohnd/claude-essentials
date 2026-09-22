# Reading fine print

## Why crop

Read resizes large images to fit the model's image limits and re-encodes images
over about 500 KB as JPEG, so small print (lot codes, expiry dates, net weights,
receipt totals) can become illegible. Cropping the region first keeps it sharp.

## Commands

- Grid: `image_tool.py tile FILE --grid 2x2`
  (columns x rows). Use a finer grid for dense documents, e.g. `--grid 2x4`; more
  than 64 tiles is refused (exit 2), so crop a region instead.
- One region: `image_tool.py tile FILE --region X,Y,W,H` in whole pixels, after you
  located the text on the whole image. A malformed region, or one outside the
  image, exits 2 with the image size; fix the numbers and run it again.
- Enlarge: add `--scale 2` (ImageMagick only) when the crop is still small.

Each output line is `<crop path> <- <original> region x=… y=… w=… h=…`. View the
crop; cite the **original file and region**, never the temporary crop path.

## Procedure

1. View the whole image to find where the relevant text is.
2. Crop that region (or tile the image) and view the crops.
3. Transcribe from the crop, and cite `file region x=… y=… w=… h=…`.
4. If the crop is still unreadable, say so. Do not reconstruct characters from
   context ("it's probably 2028 because the label says EXP").

## Pitfalls

- Photos taken sideways: `convert` applies the EXIF orientation only through
  ImageMagick; `sips` and `heif-convert` keep the stored orientation, so read a
  rotated result as rotated and say so. If text looks
  rotated in a directly readable JPEG, convert it first and read the output.
- Crops of a HEIC or TIFF must be taken from its converted PNG; tile the PNG and
  cite the original file with page and region.
- Without ImageMagick, `sips` crops on macOS; without either, read the whole
  image and flag fine print as not verified.

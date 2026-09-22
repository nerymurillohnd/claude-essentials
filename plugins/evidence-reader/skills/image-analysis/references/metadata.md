# Image metadata

## What `info` shows

`image_tool.py info FILE` prints the EXIF,
XMP, IPTC, PNG text and composite fields exiftool finds (capture and modify
dates, software, camera make and model, dimensions, orientation). Add
`--all-metadata` for container internals when a question needs them.

## How to cite it

- As a claim: "according to the metadata, `label.jpg meta EXIF:ModifyDate` is
  2026:08:14 09:30:00". Metadata is written by software and can be edited, so it
  proves nothing alone.
- A `Software` tag naming an editor is a fact about the file, not proof of
  manipulation. Do not conclude an image was altered; report the tag.
- Missing metadata is normal (messaging apps and screenshots strip it). Report
  "no capture metadata", not "the photo is fake".

## Sensitive fields

GPS coordinates, device serial numbers, the people fields (owner, artist,
author, creator, IPTC by-line, writer, the creator's contact details) and the
place fields (city, state, country, sub-location) are withheld by default.
Tool fields such as `CreatorTool` and `Software` are evidence and stay visible; `info` lists their names under `meta withheld`. Report that
they exist. Pass `--include-sensitive` only when the user explicitly asked for
location or device identity, and say in the report that you did.

## Without exiftool

`info` still gives format, dimensions, page count and SHA-256 from the file
itself. Report capture dates and camera details as **Not verified: exiftool not
installed**.

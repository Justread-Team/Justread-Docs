#!/usr/bin/env python3
"""Standalone JustRead extension packer. Python 3.10+, standard library only.

Checks package structure and documented field/resource bounds; does not execute
Lua, fully decode PNG/TTF, emulate firmware, or contact a market service.
"""
# SPDX-License-Identifier: Apache-2.0
import argparse
import io
import json
from pathlib import Path
import re
import struct
import sys
import zipfile
import zlib

KIB = 1024
MIB = KIB * KIB


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def fields(obj, allowed, required, context):
    require(isinstance(obj, dict), f"{context}: expected object")
    require(not set(obj) - set(allowed), f"{context}: unsupported fields: {set(obj) - set(allowed)}")
    require(set(required) <= set(obj), f"{context}: missing fields: {set(required) - set(obj)}")


def integer(value, low, high, context):
    require(type(value) is int and low <= value <= high,
            f"{context}: expected integer {low}..{high}")


def text(value, maximum, context, nonempty=False):
    require(isinstance(value, str), f"{context}: expected string")
    require("\0" not in value and len(value.encode("utf-8")) <= maximum,
            f"{context}: NUL or UTF-8 size exceeds {maximum} bytes")
    require(not nonempty or bool(value.strip()), f"{context}: cannot be empty")


def safe_name(name):
    # Restrict resource names to a portable subset, also usable by ui.image.
    require(isinstance(name, str) and 0 < len(name.encode("utf-8")) <= 159
            and re.fullmatch(r"[A-Za-z0-9_./-]+", name)
            and all(part not in ("", ".", "..") for part in name.split("/")),
            f"unsafe resource name: {name!r}")
    require(not name.lower().endswith((".zip", ".jrpack", ".lspack", ".tppack")),
            f"nested package is not allowed: {name}")


def rectangle(obj, context):
    for key in ("x", "y", "width", "height"):
        require(key in obj, f"{context}: missing {key}")
        integer(obj[key], -4096 if key in ("x", "y") else 1, 4096, f"{context}.{key}")


def script(data, context):
    require(0 < len(data) <= 64 * KIB, f"{context}: source must be 1..65536 bytes")
    require(b"\0" not in data and not data.startswith(b"\x1bLua"),
            f"{context}: UTF-8 text source required, no NUL or bytecode")
    data.decode("utf-8")


def lockscreen(files, market):
    def read_json(name):
        require(name in files, f"missing {name}")
        require(0 < len(files[name]) <= 64 * KIB, f"{name}: expected 1..65536 bytes")
        return json.loads(files[name].decode("utf-8"), object_pairs_hook=unique_object)

    def resource(name, suffix, limit):
        safe_name(name)
        require(name.lower().endswith(suffix) and name in files, f"missing/invalid resource: {name}")
        require(0 < len(files[name]) <= limit, f"resource size exceeds limit: {name}")

    def png(name):
        resource(name, ".png", 2 * MIB)
        data = files[name]
        require(len(data) >= 33 and data[:8] == b"\x89PNG\r\n\x1a\n"
                and data[8:16] == b"\0\0\0\rIHDR", f"invalid PNG header: {name}")
        w, h, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", data[16:29])
        require(1 <= w <= 4096 and 1 <= h <= 4096 and w * h <= 1048576,
                f"PNG dimensions exceed limits: {name}")
        require(depth == 8 and color in (0, 2, 3, 4, 6)
                and compression == filtering == interlace == 0,
                f"PNG must be 8-bit and noninterlaced: {name}")
        require(zlib.crc32(data[12:29]) == struct.unpack(">I", data[29:33])[0],
                f"PNG IHDR CRC mismatch: {name}")
        return w, h

    cfg = read_json("lockscreen.json")
    fields(cfg, ("version", "模板名称", "name", "canvas", "texts", "font_file", "glyphs", "lua"),
           ("version", "canvas", "texts"), "lockscreen.json")
    integer(cfg["version"], 1, 1, "version")
    text(cfg.get("模板名称", cfg.get("name")), 95, "模板名称", nonempty=True)
    canvas = cfg["canvas"]
    fields(canvas, ("width", "height", "background"), ("width", "height"), "canvas")
    for key in ("width", "height"):
        integer(canvas[key], 1, 4096, "canvas." + key)
    integer(canvas.get("background", 255), 0, 255, "canvas.background")
    require(isinstance(cfg["texts"], list) and len(cfg["texts"]) <= 32, "texts: expected at most 32 items")
    for item in cfg["texts"]:
        fields(item, ("text", "x", "y", "width", "height", "font_size", "gray", "align"),
               ("text", "x", "y", "width", "height", "font_size"), "texts[]")
        rectangle(item, "texts[]")
        text(item["text"], 1023, "texts[].text")
        integer(item["font_size"], 1, 256, "font_size")
        integer(item.get("gray", 0), 0, 255, "gray")
        require(item.get("align", "left") in ("left", "center", "right"), "invalid align")
    images = read_json("images.json")
    require(isinstance(images, list) and len(images) <= 32, "images.json: expected at most 32 items")
    for image in images:
        fields(image, ("file", "x", "y", "width", "height", "fit"),
               ("file", "x", "y", "width", "height"), "images[]")
        rectangle(image, "images[]")
        png(image["file"])
        require(image.get("fit", "contain") in ("contain", "stretch"), "invalid image fit")
    if "font_file" in cfg and cfg["font_file"] != "system":
        resource(cfg["font_file"], ".ttf", 2 * MIB)
    if "glyphs" in cfg:
        glyph = cfg["glyphs"]
        fields(glyph, ("file", "characters", "cell_width", "cell_height"),
               ("file", "characters", "cell_width", "cell_height"), "glyphs")
        chars = glyph["characters"]
        require(isinstance(chars, str) and 1 <= len(chars) <= 31 and len(set(chars)) == len(chars)
                and all(33 <= ord(ch) <= 126 for ch in chars), "invalid glyph characters")
        for key in ("cell_width", "cell_height"):
            integer(glyph[key], 1, 512, "glyphs." + key)
        require(png(glyph["file"]) == (len(chars) * glyph["cell_width"], glyph["cell_height"]),
                "glyph atlas dimensions do not match character cells")
    if "lua" in cfg:
        lua = cfg["lua"]
        fields(lua, ("file", "when", "interval_ms", "hold_ms", "area", "refresh", "ancs", "ble"),
               ("file", "when", "area"), "lua")
        resource(lua["file"], ".lua", 64 * KIB)
        require("/" not in lua["file"] and lua["file"].endswith(".lua"), "lua.file must be root-level lowercase .lua")
        script(files[lua["file"]], lua["file"])
        require(lua["when"] in ("before_lock", "before_open", "locked"), "invalid lua.when")
        area = lua["area"]
        fields(area, ("x", "y", "width", "height"), ("x", "y", "width", "height"), "lua.area")
        rectangle(area, "lua.area")
        require(area["x"] >= 0 and area["y"] >= 0
                and area["x"] + area["width"] <= canvas["width"]
                and area["y"] + area["height"] <= canvas["height"], "lua.area must fit canvas")
        for key, required, low, high in (("interval_ms", lua["when"] == "locked", 1000, 86400000),
                                         ("hold_ms", lua["when"] == "before_open", 250, 600000)):
            require(not required or key in lua, "lua: missing " + key)
            if key in lua:
                integer(lua[key], low, high, "lua." + key)
        require(lua.get("refresh", "partial_bw") in ("partial_bw", "partial_gray", "full_gray", "full_gc16"),
                "invalid lua.refresh (JSON enum differs from ui.refresh)")
        for key in ("ancs", "ble"):
            require(key not in lua or type(lua[key]) is bool, "lua." + key + " must be boolean")
    for name, data in files.items():
        if name.lower().endswith(".png"):
            png(name)
        elif name.lower().endswith(".lua"):
            script(data, name)
        if market and name not in ("lockscreen.json", "images.json"):
            lower = name.lower()
            if lower in ("ofl.txt", "license.txt", "font-license.rtf"):
                require(0 < len(data) <= 128 * KIB and bool(data.decode("utf-8").strip()), "invalid font license")
                require(not lower.endswith(".rtf") or data.decode("utf-8").lstrip().startswith("{\\rtf"), "invalid RTF license")
            else:
                require(lower.endswith((".png", ".lua")), f"current market does not accept {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("plugin", "lockscreen"))
    parser.add_argument("source", type=Path, help="directory containing root entry files")
    parser.add_argument("output", type=Path, help="output .jrpack or .lspack, outside source")
    parser.add_argument("--market", action="store_true", help="also apply current market file types and 8 MiB upload ceiling")
    parser.add_argument("--force", action="store_true", help="replace an existing output file")
    args = parser.parse_args()
    try:
        require(args.source.is_dir() and not args.source.is_symlink(), "source must be a real directory")
        source = args.source.resolve()
        require(not args.output.resolve().is_relative_to(source), "output must be outside the source directory")
        require(not args.output.is_symlink(), "output cannot be a symbolic link")
        require(not args.output.exists() or args.force, "output exists; use --force to replace it")
        suffix = ".jrpack" if args.kind == "plugin" else ".lspack"
        require(args.output.suffix.lower() == suffix, "output must end in " + suffix)
        paths = []
        for path in sorted(source.rglob("*")):
            require(not path.is_symlink(), f"symbolic link is not allowed: {path.name}")
            if path.is_dir():
                continue
            require(path.is_file(), f"not a regular file: {path.name}")
            name = path.relative_to(source).as_posix()
            safe_name(name)
            if args.kind == "plugin":
                require(len(name) <= 96, "plugin resource path exceeds 96 bytes: " + name)
            paths.append((name, path))
        require(0 < len(paths) <= 128, "expected 1..128 files")
        limit = 8 * MIB if args.kind == "plugin" else 16 * MIB
        require(sum(path.stat().st_size for _, path in paths) <= limit, "total resource size exceeds package limit")
        files = {name: path.read_bytes() for name, path in paths}
        if args.kind == "plugin":
            require("main.lua" in files, "plugin source root must contain main.lua")
            script(files["main.lua"], "main.lua")
        else:
            lockscreen(files, args.market)
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
            for name, data in files.items():
                info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_STORED
                archive.writestr(info, data)
        data = output.getvalue()
        if args.kind == "plugin" or args.market:
            require(len(data) <= 8 * MIB, "final ZIP exceeds 8 MiB (including ZIP metadata)")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("wb" if args.force else "xb") as target:
            target.write(data)
        import hashlib
        print(f"OK: {args.output} ({len(data)} bytes)")
        print("SHA-256:", hashlib.sha256(data).hexdigest())
        print("Structure checks passed; Lua execution, full image/font decoding, hardware and market review were not tested.")
    except (OSError, ValueError, TypeError, KeyError, struct.error, zipfile.LargeZipFile) as error:
        parser.exit(2, f"ERROR: {error}\n")


if __name__ == "__main__":
    main()

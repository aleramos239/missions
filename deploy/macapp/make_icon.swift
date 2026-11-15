// swift make_icon.swift  ->  Missions.icns (SF Symbol "flag.checkered" on a rounded square)
import Cocoa
let here = URL(fileURLWithPath: CommandLine.arguments[0]).deletingLastPathComponent().path
let set = NSTemporaryDirectory() + "Missions.iconset"
try? FileManager.default.removeItem(atPath: set)
try! FileManager.default.createDirectory(atPath: set, withIntermediateDirectories: true)
func png(_ px: Int) -> Data {
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: px, pixelsHigh: px, bitsPerSample: 8, samplesPerPixel: 4,
                               hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    let s = CGFloat(px), r = NSRect(x: s*0.06, y: s*0.06, width: s*0.88, height: s*0.88)
    let p = NSBezierPath(roundedRect: r, xRadius: s*0.2, yRadius: s*0.2)
    NSGradient(colors: [NSColor(red: 0.10, green: 0.45, blue: 0.40, alpha: 1), NSColor(red: 0.04, green: 0.20, blue: 0.24, alpha: 1)])!.draw(in: p, angle: -90)
    let cfg = NSImage.SymbolConfiguration(pointSize: s*0.5, weight: .semibold).applying(.init(paletteColors: [.white]))
    let sym = NSImage(systemSymbolName: "flag.checkered", accessibilityDescription: nil)!.withSymbolConfiguration(cfg)!
    let w = sym.size.width, h = sym.size.height
    sym.draw(in: NSRect(x: (s-w)/2, y: (s-h)/2, width: w, height: h))
    NSGraphicsContext.restoreGraphicsState()
    return rep.representation(using: .png, properties: [:])!
}
for sz in [16, 32, 128, 256, 512] {
    for sc in [1, 2] {
        try! png(sz * sc).write(to: URL(fileURLWithPath: "\(set)/icon_\(sz)x\(sz)\(sc == 2 ? "@2x" : "").png"))
    }
}
let p = Process(); p.launchPath = "/usr/bin/iconutil"; p.arguments = ["-c", "icns", set, "-o", here + "/Missions.icns"]
try! p.run(); p.waitUntilExit()

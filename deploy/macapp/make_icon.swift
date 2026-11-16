// swift make_icon.swift  ->  Missions.icns (a white crosshair on a near-black rounded tile, like Homebase)
import Cocoa
let here = URL(fileURLWithPath: CommandLine.arguments[0]).deletingLastPathComponent().path
func png(_ px: Int) -> Data {
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: px, pixelsHigh: px, bitsPerSample: 8, samplesPerPixel: 4,
                               hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    let s = CGFloat(px)
    NSColor(red: 10/255, green: 10/255, blue: 10/255, alpha: 1).setFill()
    NSBezierPath(roundedRect: NSRect(x: s*0.0977, y: s*0.0977, width: s*0.805, height: s*0.805), xRadius: s*0.18, yRadius: s*0.18).fill()
    func P(_ x: CGFloat, _ y: CGFloat) -> NSPoint { NSPoint(x: s*x, y: s*(1-y)) }  // fractions of s, y measured from the top
    let p = NSBezierPath()
    p.lineWidth = s*0.0566; p.lineCapStyle = .round; p.lineJoinStyle = .round
    p.appendOval(in: NSRect(x: s*0.30, y: s*0.30, width: s*0.40, height: s*0.40))  // ring, radius 0.20
    for (dx, dy) in [(0, -1), (1, 0), (0, 1), (-1, 0)] as [(CGFloat, CGFloat)] {  // four ticks, 0.14 -> 0.25 from centre
        p.move(to: P(0.5 + dx*0.14, 0.5 + dy*0.14)); p.line(to: P(0.5 + dx*0.25, 0.5 + dy*0.25))
    }
    NSColor.white.set(); p.stroke()
    NSGraphicsContext.restoreGraphicsState()
    return rep.representation(using: .png, properties: [:])!
}
let set = NSTemporaryDirectory() + "Missions.iconset"
try? FileManager.default.removeItem(atPath: set)
try! FileManager.default.createDirectory(atPath: set, withIntermediateDirectories: true)
for sz in [16, 32, 128, 256, 512] {
    for sc in [1, 2] {
        try! png(sz * sc).write(to: URL(fileURLWithPath: "\(set)/icon_\(sz)x\(sz)\(sc == 2 ? "@2x" : "").png"))
    }
}
let p = Process(); p.launchPath = "/usr/bin/iconutil"; p.arguments = ["-c", "icns", set, "-o", here + "/Missions.icns"]
try! p.run(); p.waitUntilExit()

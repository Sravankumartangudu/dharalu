// Draws the WheatWise app icon and writes Icon/AppIcon.icns.
// Run: swift Icon/make_icon.swift   (from the mac/ folder)
//
// Motif: a golden ear of wheat over a faint rising price line, on a deep field-green tile.

import AppKit

let S: CGFloat = 1024

func drawIcon(in ctx: CGContext) {
    let cs = CGColorSpaceCreateDeviceRGB()
    func color(_ hex: UInt32, _ a: CGFloat = 1) -> CGColor {
        CGColor(red: CGFloat((hex >> 16) & 0xff) / 255, green: CGFloat((hex >> 8) & 0xff) / 255,
                blue: CGFloat(hex & 0xff) / 255, alpha: a)
    }
    func grad(_ stops: [(UInt32, CGFloat, CGFloat)]) -> CGGradient {
        CGGradient(colorsSpace: cs, colors: stops.map { color($0.0, $0.1) } as CFArray,
                   locations: stops.map { $0.2 })!
    }

    // Tile: macOS-style rounded square.
    let inset: CGFloat = 100
    let tile = CGRect(x: inset, y: inset, width: S - 2 * inset, height: S - 2 * inset)
    let tilePath = CGPath(roundedRect: tile, cornerWidth: 185, cornerHeight: 185, transform: nil)
    ctx.saveGState()
    ctx.setShadow(offset: CGSize(width: 0, height: -14), blur: 30, color: color(0x000000, 0.45))
    ctx.addPath(tilePath); ctx.setFillColor(color(0x123d2a)); ctx.fillPath()
    ctx.restoreGState()
    ctx.saveGState()
    ctx.addPath(tilePath); ctx.clip()
    ctx.drawLinearGradient(grad([(0x1f6b45, 1, 0), (0x0d2b1e, 1, 1)]),
                           start: CGPoint(x: 0, y: tile.maxY), end: CGPoint(x: 0, y: tile.minY), options: [])

    // Faint price line rising left to right.
    let line = CGMutablePath()
    let pts: [(CGFloat, CGFloat)] = [(150, 330), (260, 300), (360, 380), (470, 350), (580, 470), (690, 430), (874, 640)]
    line.move(to: CGPoint(x: pts[0].0, y: pts[0].1))
    for p in pts.dropFirst() { line.addLine(to: CGPoint(x: p.0, y: p.1)) }
    ctx.addPath(line)
    ctx.setLineWidth(22); ctx.setLineCap(.round); ctx.setLineJoin(.round)
    ctx.setStrokeColor(color(0x7fe0a8, 0.35)); ctx.strokePath()

    // Stalk.
    let base = CGPoint(x: 512, y: 170), top = CGPoint(x: 512, y: 760)
    ctx.move(to: base); ctx.addLine(to: top)
    ctx.setLineWidth(26); ctx.setStrokeColor(color(0xd9a520)); ctx.strokePath()

    // Grains: pairs of golden ellipses angled out from the stalk, smaller towards the tip.
    func grain(at c: CGPoint, angle: CGFloat, w: CGFloat, h: CGFloat) {
        ctx.saveGState()
        ctx.translateBy(x: c.x, y: c.y); ctx.rotate(by: angle)
        let r = CGRect(x: -w / 2, y: -h / 2, width: w, height: h)
        ctx.addPath(CGPath(ellipseIn: r, transform: nil)); ctx.clip()
        ctx.drawLinearGradient(grad([(0xffe08a, 1, 0), (0xf2b424, 1, 0.55), (0xc98500, 1, 1)]),
                               start: CGPoint(x: -w / 2, y: h / 2), end: CGPoint(x: w / 2, y: -h / 2), options: [])
        ctx.restoreGState()
    }
    for i in 0..<6 {
        let y = 380 + CGFloat(i) * 62
        let k = 1 - CGFloat(i) * 0.07
        grain(at: CGPoint(x: 512 - 46 * k, y: y), angle: 0.5, w: 74 * k, h: 140 * k)
        grain(at: CGPoint(x: 512 + 46 * k, y: y), angle: -0.5, w: 74 * k, h: 140 * k)
    }
    grain(at: CGPoint(x: 512, y: 770), angle: 0, w: 62, h: 124)

    // Two leaves at the base.
    for (dx, ang) in [(-1.0, 0.9), (1.0, -0.9)] as [(CGFloat, CGFloat)] {
        ctx.saveGState()
        ctx.translateBy(x: 512 + dx * 62, y: 265); ctx.rotate(by: ang)
        ctx.addPath(CGPath(ellipseIn: CGRect(x: -28, y: -100, width: 56, height: 200), transform: nil))
        ctx.setFillColor(color(0x5cc98a)); ctx.fillPath()
        ctx.restoreGState()
    }

    ctx.restoreGState()   // end tile clip
}

func render(_ px: Int) -> Data {
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: px, pixelsHigh: px, bitsPerSample: 8,
                               samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                               colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    let g = NSGraphicsContext(bitmapImageRep: rep)!
    let ctx = g.cgContext
    ctx.scaleBy(x: CGFloat(px) / S, y: CGFloat(px) / S)
    drawIcon(in: ctx)
    return rep.representation(using: .png, properties: [:])!
}

let root = URL(fileURLWithPath: CommandLine.arguments[0]).deletingLastPathComponent()
let iconset = root.appendingPathComponent("AppIcon.iconset")
try? FileManager.default.removeItem(at: iconset)
try! FileManager.default.createDirectory(at: iconset, withIntermediateDirectories: true)
for base in [16, 32, 128, 256, 512] {
    try! render(base).write(to: iconset.appendingPathComponent("icon_\(base)x\(base).png"))
    try! render(base * 2).write(to: iconset.appendingPathComponent("icon_\(base)x\(base)@2x.png"))
}
try! render(1024).write(to: root.appendingPathComponent("preview.png"))
let p = Process()
p.executableURL = URL(fileURLWithPath: "/usr/bin/iconutil")
p.arguments = ["-c", "icns", iconset.path, "-o", root.appendingPathComponent("AppIcon.icns").path]
try! p.run(); p.waitUntilExit()
try? FileManager.default.removeItem(at: iconset)
print(p.terminationStatus == 0 ? "Wrote \(root.path)/AppIcon.icns" : "iconutil failed")

// Draws the Dharalu app icon and writes Icon/AppIcon.icns.
// Run: swift Icon/make_icon.swift   (from the mac/ folder)
//
// Motif: a gold balance (⚖️) weighing an ear of wheat against a gold coin, over a faint price
// line, on a deep indigo tile - "what is it worth today".

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
    let goldGrad = grad([(0xffe08a, 1, 0), (0xf2b424, 1, 0.55), (0xc98500, 1, 1)])

    // Tile: macOS-style rounded square.
    let inset: CGFloat = 100
    let tile = CGRect(x: inset, y: inset, width: S - 2 * inset, height: S - 2 * inset)
    let tilePath = CGPath(roundedRect: tile, cornerWidth: 185, cornerHeight: 185, transform: nil)
    ctx.saveGState()
    ctx.setShadow(offset: CGSize(width: 0, height: -14), blur: 30, color: color(0x000000, 0.45))
    ctx.addPath(tilePath); ctx.setFillColor(color(0x1b1f4a)); ctx.fillPath()
    ctx.restoreGState()
    ctx.saveGState()
    ctx.addPath(tilePath); ctx.clip()
    ctx.drawLinearGradient(grad([(0x2e3a8c, 1, 0), (0x121433, 1, 1)]),
                           start: CGPoint(x: 0, y: tile.maxY), end: CGPoint(x: 0, y: tile.minY), options: [])

    // Faint price line: past (solid) then forecast (dashed).
    let pts: [(CGFloat, CGFloat)] = [(130, 300), (240, 340), (330, 290), (430, 360), (520, 330)]
    let past = CGMutablePath()
    past.move(to: CGPoint(x: pts[0].0, y: pts[0].1))
    for p in pts.dropFirst() { past.addLine(to: CGPoint(x: p.0, y: p.1)) }
    ctx.addPath(past)
    ctx.setLineWidth(18); ctx.setLineCap(.round); ctx.setLineJoin(.round)
    ctx.setStrokeColor(color(0x9fb3ff, 0.30)); ctx.strokePath()
    ctx.move(to: CGPoint(x: 520, y: 330)); ctx.addLine(to: CGPoint(x: 900, y: 420))
    ctx.setLineDash(phase: 0, lengths: [26, 26])
    ctx.setStrokeColor(color(0x9fb3ff, 0.22)); ctx.strokePath()
    ctx.setLineDash(phase: 0, lengths: [])

    // Fills a path with the gold gradient.
    func gold(_ path: CGPath) {
        ctx.saveGState()
        ctx.addPath(path); ctx.clip()
        let b = path.boundingBox
        ctx.drawLinearGradient(goldGrad, start: CGPoint(x: b.minX, y: b.maxY), end: CGPoint(x: b.maxX, y: b.minY), options: [])
        ctx.restoreGState()
    }

    // Base and post.
    gold(CGPath(roundedRect: CGRect(x: 372, y: 176, width: 280, height: 46), cornerWidth: 23, cornerHeight: 23, transform: nil))
    gold(CGPath(roundedRect: CGRect(x: 492, y: 210, width: 40, height: 520), cornerWidth: 20, cornerHeight: 20, transform: nil))
    gold(CGPath(ellipseIn: CGRect(x: 478, y: 716, width: 68, height: 68), transform: nil))

    // Beam.
    gold(CGPath(roundedRect: CGRect(x: 236, y: 690, width: 552, height: 30), cornerWidth: 15, cornerHeight: 15, transform: nil))

    // Strings and pans.
    for cx in [276, 748] as [CGFloat] {
        ctx.move(to: CGPoint(x: cx, y: 700)); ctx.addLine(to: CGPoint(x: cx - 92, y: 468))
        ctx.move(to: CGPoint(x: cx, y: 700)); ctx.addLine(to: CGPoint(x: cx + 92, y: 468))
        ctx.setLineWidth(9); ctx.setStrokeColor(color(0xf2b424)); ctx.strokePath()
        let pan = CGMutablePath()
        pan.move(to: CGPoint(x: cx - 120, y: 468))
        pan.addQuadCurve(to: CGPoint(x: cx + 120, y: 468), control: CGPoint(x: cx, y: 360))
        pan.closeSubpath()
        gold(pan)
    }

    // Left pan: an ear of wheat.
    func grain(at c: CGPoint, angle: CGFloat, w: CGFloat, h: CGFloat) {
        ctx.saveGState()
        ctx.translateBy(x: c.x, y: c.y); ctx.rotate(by: angle)
        ctx.addPath(CGPath(ellipseIn: CGRect(x: -w / 2, y: -h / 2, width: w, height: h), transform: nil))
        ctx.setFillColor(color(0xfff1c2)); ctx.fillPath()
        ctx.restoreGState()
    }
    ctx.move(to: CGPoint(x: 276, y: 470)); ctx.addLine(to: CGPoint(x: 276, y: 640))
    ctx.setLineWidth(9); ctx.setStrokeColor(color(0xfff1c2)); ctx.strokePath()
    for i in 0..<4 {
        let y = 512 + CGFloat(i) * 34, k = 1 - CGFloat(i) * 0.1
        grain(at: CGPoint(x: 276 - 20 * k, y: y), angle: 0.5, w: 30 * k, h: 58 * k)
        grain(at: CGPoint(x: 276 + 20 * k, y: y), angle: -0.5, w: 30 * k, h: 58 * k)
    }
    grain(at: CGPoint(x: 276, y: 648), angle: 0, w: 26, h: 52)

    // Right pan: a gold coin with a ₹ mark.
    let coin = CGRect(x: 748 - 70, y: 470, width: 140, height: 140)
    ctx.addPath(CGPath(ellipseIn: coin, transform: nil)); ctx.setFillColor(color(0xfff1c2)); ctx.fillPath()
    ctx.addPath(CGPath(ellipseIn: coin.insetBy(dx: 14, dy: 14), transform: nil))
    ctx.setLineWidth(8); ctx.setStrokeColor(color(0xc98500)); ctx.strokePath()
    let rupee = NSAttributedString(string: "₹", attributes: [.font: NSFont.systemFont(ofSize: 86, weight: .bold),
                                                             .foregroundColor: NSColor(cgColor: color(0xa86f00))!])
    let line = CTLineCreateWithAttributedString(rupee)
    let lb = CTLineGetBoundsWithOptions(line, .useGlyphPathBounds)
    ctx.textPosition = CGPoint(x: coin.midX - lb.midX, y: coin.midY - lb.midY)
    CTLineDraw(line, ctx)

    ctx.restoreGState()   // end tile clip
}

func renderFull(_ px: Int) -> Data {
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: px, pixelsHigh: px, bitsPerSample: 8,
                               samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                               colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    let g = NSGraphicsContext(bitmapImageRep: rep)!
    let ctx = g.cgContext
    ctx.scaleBy(x: CGFloat(px) / S, y: CGFloat(px) / S)
    drawIcon(in: ctx)
    return rep.representation(using: .png, properties: [:])!
}

// Every size is shrunk from one full-size drawing. Shadow and glow blur are measured in device pixels, so
// drawing straight at 16–64 px let them spill over the whole image as a faint grey square.
enum Full {
    static let png = renderFull(1024)
    static let image = NSBitmapImageRep(data: png)!.cgImage!
}

func render(_ px: Int) -> Data {
    if px == Full.image.width { return Full.png }
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: px, pixelsHigh: px, bitsPerSample: 8,
                               samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                               colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    let ctx = NSGraphicsContext(bitmapImageRep: rep)!.cgContext
    ctx.interpolationQuality = .high
    ctx.draw(Full.image, in: CGRect(x: 0, y: 0, width: px, height: px))
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

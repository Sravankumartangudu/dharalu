// WheatWise for Mac - a menu-bar companion to the WheatWise dashboard.
//
// It reads the same latest.json that GitHub Actions publishes twice a day, shows today's
// BUY / SELL call in the menu bar with the proof behind it, notifies you when the call
// changes or the price jumps, and opens the full dashboard in its own window.
// Nothing is computed here - the agent runs on GitHub; this app only reads its output.

import AppKit
import ServiceManagement
import UserNotifications
import WebKit

let appName = "WheatWise"
let defaultDataURL = "https://sravankumartangudu.github.io/wheatwise/data/latest.json"
let repoURL = "https://github.com/Sravankumartangudu/wheatwise"
let moveAlertPct = 2.5

// MARK: - Settings

enum Settings {
    static let d = UserDefaults.standard
    static var dataURL: String {
        get { d.string(forKey: "dataURL") ?? defaultDataURL }
        set { d.set(newValue, forKey: "dataURL") }
    }
    static var siteURL: URL {
        let s = dataURL.replacingOccurrences(of: "data/latest.json", with: "")
        return URL(string: s) ?? URL(string: "https://sravankumartangudu.github.io/wheatwise/")!
    }
    static var showPrice: Bool {
        get { d.object(forKey: "showPrice") as? Bool ?? true }
        set { d.set(newValue, forKey: "showPrice") }
    }
    static var notify: Bool {
        get { d.object(forKey: "notify") as? Bool ?? true }
        set { d.set(newValue, forKey: "notify") }
    }
    static var minutes: Int {
        get { d.object(forKey: "minutes") as? Int ?? 30 }
        set { d.set(newValue, forKey: "minutes") }
    }
    /// "system" (follow macOS, Auto included), "light" or "dark".
    static var appearance: String {
        get { let v = d.string(forKey: "appearance") ?? "system"; return ["system", "light", "dark"].contains(v) ? v : "system" }
        set { d.set(newValue, forKey: "appearance") }
    }
    static func applyAppearance() {
        switch appearance {
        case "light": NSApp.appearance = NSAppearance(named: .aqua)
        case "dark": NSApp.appearance = NSAppearance(named: .darkAqua)
        default: NSApp.appearance = nil
        }
    }
    /// JS that makes the dashboard page match the choice (same `ww.theme` key the page's own toggle uses).
    static var themeScript: String {
        let v = appearance
        return v == "system"
            ? "try{localStorage.removeItem('ww.theme');delete document.documentElement.dataset.theme;}catch(e){}"
            : "try{localStorage.setItem('ww.theme','\"\(v)\"');document.documentElement.dataset.theme='\(v)';}catch(e){}"
    }
    static var lastSignal: String? {
        get { d.string(forKey: "lastSignal") }
        set { d.set(newValue, forKey: "lastSignal") }
    }
    static var lastMoveAlert: String? {
        get { d.string(forKey: "lastMoveAlert") }
        set { d.set(newValue, forKey: "lastMoveAlert") }
    }
}

// MARK: - The agent's output (a subset of docs/data/latest.json)

struct Latest: Decodable {
    struct Bench: Decodable { let price: Double; let chg_1d: Double?; let chg_7d: Double?; let chg_30d: Double? }
    struct Evidence: Decodable { let rule: String; let value: String; let test: String; let points: Int; let source: String; let why: String }
    struct Signal: Decodable {
        let score: Int; let max_score: Int; let confidence: String; let key: String
        let label: String; let telugu: String; let buyer: String; let holder: String
        let evidence: [Evidence]
    }
    struct Point: Decodable { let date: String; let price: Double; let low: Double; let high: Double }
    struct Source: Decodable { let market: String; let landed: Double; let mandi_price: Double; let km: Double }
    struct MSP: Decodable { let floor: Double; let season: String? }
    struct Group: Decodable { let days: Int; let avg_move_pct: Double; let rose_pct: Double; let beat_holding_cost_pct: Double }
    struct Summary: Decodable { let buy_days: Group?; let hold_days: Group?; let wait_days: Group?; let sell_days: Group? }
    struct Live: Decodable { let calls: Int; let graded: Int; let right_pct: Double? }
    struct Record: Decodable { let summary: Summary; let summary_all: Summary?; let since: String?; let live: Live? }
    struct Brief: Decodable { let english: String; let telugu: String }
    struct Briefing: Decodable { let rules: Brief; let ai: Brief? }
    struct Timing: Decodable { let cheapest_months: [String]; let dearest_months: [String]; let days_to_buy_window: Int }

    let asof: String
    let generated_at: String?
    let benchmark: Bench
    let signal: Signal
    let forecast_points: [String: Point]
    let best_source: Source?
    let msp: MSP
    let track_record: Record
    let briefing: Briefing
    let timing: Timing
    let carrying_cost_30d_pct: Double?

    var brief: Brief { briefing.ai ?? briefing.rules }
    var generated: Date? { generated_at.flatMap { ISO8601DateFormatter().date(from: $0) } }
}

// MARK: - Formatting

func rs(_ v: Double) -> String {
    let f = NumberFormatter()
    f.numberStyle = .decimal
    f.locale = Locale(identifier: "en_IN")   // 2,92,784 - the Indian grouping
    f.maximumFractionDigits = 0
    return "₹" + (f.string(from: NSNumber(value: v.rounded())) ?? "\(Int(v))")
}

func pc(_ v: Double?) -> String {
    guard let v = v else { return "–" }
    return String(format: "%@%.1f%%", v > 0 ? "+" : "", v)
}

func signed(_ n: Int) -> String { n > 0 ? "+\(n)" : n < 0 ? "−\(-n)" : "0" }

func prettyDate(_ iso: String) -> String {
    let p = DateFormatter(); p.dateFormat = "yyyy-MM-dd"
    guard let d = p.date(from: iso) else { return iso }
    let f = DateFormatter(); f.dateFormat = "d MMM yyyy"
    return f.string(from: d)
}

/// Menus don't wrap text, so long lines are broken by hand.
func wrap(_ text: String, _ width: Int = 64) -> String {
    text.components(separatedBy: "\n").map { para -> String in
        var lines: [String] = [], line = ""
        for word in para.split(separator: " ") {
            if line.count + word.count + 1 > width, !line.isEmpty { lines.append(line); line = "" }
            line += (line.isEmpty ? "" : " ") + word
        }
        if !line.isEmpty { lines.append(line) }
        return lines.joined(separator: "\n")
    }.joined(separator: "\n")
}

func signalColor(_ key: String) -> NSColor {
    switch key {
    case "STRONG_BUY", "BUY": return NSColor(srgbRed: 0.05, green: 0.64, blue: 0.05, alpha: 1)
    case "HOLD": return NSColor(srgbRed: 0.79, green: 0.52, blue: 0.0, alpha: 1)
    case "SELL", "STRONG_SELL": return NSColor(srgbRed: 0.82, green: 0.23, blue: 0.23, alpha: 1)
    default: return NSColor.secondaryLabelColor
    }
}

// MARK: - App

final class App: NSObject, NSApplicationDelegate, NSMenuDelegate, UNUserNotificationCenterDelegate {
    let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    let dashboard = Dashboard()
    var latest: Latest?
    var lastError: String?
    var fetchedAt: Date?
    var timer: Timer?

    func applicationDidFinishLaunching(_ n: Notification) {
        NexusBeacon.start(name: appName) { [weak self] in
            guard let self = self else { return ("ok", "") }
            if let e = self.lastError { return ("error", e) }
            guard let l = self.latest else { return ("ok", "starting") }
            if self.isStale { return ("warn", "data is \(self.ageHours)h old") }
            return ("ok", "\(l.signal.label) \(rs(l.benchmark.price))")
        }
        Settings.applyAppearance()
        installEditMenu()
        let menu = NSMenu()
        menu.delegate = self
        item.menu = menu
        NexusBeacon.attach(item)   // lets the app live in Nexus's menu
        item.button?.toolTip = "WheatWise - wheat buy/sell agent"
        updateTitle()
        let center = UNUserNotificationCenter.current()
        center.delegate = self
        center.requestAuthorization(options: [.alert, .sound]) { _, _ in }
        schedule()
        refresh()
        if CommandLine.arguments.contains("--dashboard") { dashboard.show() }
    }

    func schedule() {
        timer?.invalidate()
        let t = Timer(timeInterval: TimeInterval(Settings.minutes * 60), repeats: true) { [weak self] _ in self?.refresh() }
        RunLoop.main.add(t, forMode: .common)
        timer = t
    }

    var ageHours: Int { Int((Date().timeIntervalSince(latest?.generated ?? Date())) / 3600) }
    /// Actions runs at 12:30 and 19:30 IST, so anything older than a day and a half means it stopped.
    var isStale: Bool { latest != nil && ageHours >= 36 }

    // MARK: Fetch

    @objc func refresh() {
        guard var comps = URLComponents(string: Settings.dataURL) else { lastError = "bad data URL"; updateTitle(); return }
        comps.queryItems = [URLQueryItem(name: "t", value: String(Int(Date().timeIntervalSince1970)))]   // skip caches
        var req = URLRequest(url: comps.url!, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 30)
        req.setValue("no-cache", forHTTPHeaderField: "Cache-Control")
        URLSession.shared.dataTask(with: req) { data, resp, err in
            var result: Latest?, problem: String?
            if let err = err {
                problem = err.localizedDescription
            } else if let h = resp as? HTTPURLResponse, h.statusCode != 200 {
                problem = "HTTP \(h.statusCode) from the dashboard"
            } else if let data = data {
                do { result = try JSONDecoder().decode(Latest.self, from: data) } catch { problem = "couldn't read latest.json (\(error))" }
            }
            DispatchQueue.main.async {
                if let r = result {
                    self.notifyIfNeeded(r)
                    self.latest = r
                    self.lastError = nil
                    self.fetchedAt = Date()
                } else {
                    self.lastError = problem ?? "no data"
                }
                self.updateTitle()
                NexusBeacon.beat()
            }
        }.resume()
    }

    func updateTitle() {
        guard let b = item.button else { return }
        guard let l = latest else {
            b.title = lastError == nil ? "🌾 …" : "🌾 ⚠︎"
            return
        }
        var t = "🌾 " + l.signal.label
        if Settings.showPrice { t += " " + rs(l.benchmark.price) }
        if isStale || lastError != nil { t += " ⚠︎" }
        b.title = t
    }

    // MARK: Notifications

    func notifyIfNeeded(_ l: Latest) {
        defer { Settings.lastSignal = l.signal.key }
        guard Settings.notify else { return }
        if let prev = Settings.lastSignal, prev != l.signal.key {
            post(id: "signal-\(l.asof)", title: "WheatWise: now \(l.signal.label) · \(l.signal.telugu)",
                 body: "Was \(prev.replacingOccurrences(of: "_", with: " ")). Score \(signed(l.signal.score)) of ±\(l.signal.max_score), confidence \(l.signal.confidence). If buying: \(l.signal.buyer) If holding: \(l.signal.holder)")
        }
        if let m = l.benchmark.chg_1d, abs(m) >= moveAlertPct, Settings.lastMoveAlert != l.asof {
            Settings.lastMoveAlert = l.asof
            post(id: "move-\(l.asof)", title: "WheatWise: price \(m > 0 ? "up" : "down") \(pc(m)) in a day",
                 body: "Benchmark \(rs(l.benchmark.price))/qtl on \(prettyDate(l.asof)). Signal: \(l.signal.label).")
        }
    }

    func post(id: String, title: String, body: String) {
        let c = UNMutableNotificationContent()
        c.title = title
        c.body = body
        c.sound = .default
        UNUserNotificationCenter.current().add(UNNotificationRequest(identifier: id, content: c, trigger: nil))
    }

    func userNotificationCenter(_ c: UNUserNotificationCenter, willPresent n: UNNotification,
                                withCompletionHandler done: @escaping (UNNotificationPresentationOptions) -> Void) {
        done([.banner, .sound])
    }

    func userNotificationCenter(_ c: UNUserNotificationCenter, didReceive r: UNNotificationResponse,
                                withCompletionHandler done: @escaping () -> Void) {
        dashboard.show()
        done()
    }

    // MARK: Menu

    func menuNeedsUpdate(_ menu: NSMenu) {
        menu.removeAllItems()
        if let l = latest {
            buildSignal(menu, l)
        } else {
            menu.addItem(info(lastError.map { "Couldn't load today's call: \($0)" } ?? "Loading today's call…"))
        }
        if let e = lastError, latest != nil { menu.addItem(info(wrap("⚠︎ Last refresh failed: \(e) - showing the previous data."))) }
        if isStale {
            menu.addItem(info(wrap("⚠︎ This data is \(ageHours) hours old. The GitHub Actions monitor may have stopped - open the repo's Actions tab to check.")))
        }
        menu.addItem(.separator())
        menu.addItem(action("Open Dashboard…", #selector(openDashboard), "d"))
        menu.addItem(action("Open in Browser", #selector(openBrowser)))
        menu.addItem(action("Refresh Now", #selector(refresh), "r"))
        if let f = fetchedAt {
            let fmt = DateFormatter(); fmt.dateFormat = "d MMM, HH:mm"
            let gen = latest?.generated.map { fmt.string(from: $0) } ?? "?"
            menu.addItem(info("Checked \(fmt.string(from: f)) · agent ran \(gen)"))
        }
        menu.addItem(.separator())
        menu.addItem(settingsItem())
        menu.addItem(action("Help - How to Use", #selector(openHelp)))
        menu.addItem(action("Quit WheatWise", #selector(quit), "q"))
    }

    func buildSignal(_ menu: NSMenu, _ l: Latest) {
        let s = l.signal
        let head = NSMenuItem()
        let t = NSMutableAttributedString(string: "\(s.label) · \(s.telugu)\n",
                                          attributes: [.font: NSFont.boldSystemFont(ofSize: 15), .foregroundColor: signalColor(s.key)])
        t.append(NSAttributedString(string: "Score \(signed(s.score)) of ±\(s.max_score) · confidence \(s.confidence) · \(prettyDate(l.asof))",
                                    attributes: [.font: NSFont.menuFont(ofSize: 12), .foregroundColor: NSColor.secondaryLabelColor]))
        head.attributedTitle = t
        head.isEnabled = false
        menu.addItem(head)
        menu.addItem(info(wrap("If buying: \(s.buyer)")))
        menu.addItem(info(wrap("If holding stock: \(s.holder)")))
        menu.addItem(.separator())

        let b = l.benchmark
        menu.addItem(info("Benchmark \(rs(b.price))/qtl · 1d \(pc(b.chg_1d)) · 7d \(pc(b.chg_7d)) · 30d \(pc(b.chg_30d))"))
        if let f = l.forecast_points["30"] {
            menu.addItem(info("30-day forecast \(rs(f.price)) (likely \(rs(f.low)) – \(rs(f.high)))"))
        }
        if let src = l.best_source {
            menu.addItem(info("Cheapest landed at Srikakulam: \(src.market) \(rs(src.landed))"))
        }
        var floor = "MSP floor \(rs(l.msp.floor))"
        if let cc = l.carrying_cost_30d_pct { floor += " · holding cost \(String(format: "%.1f", cc))% per 30 days" }
        menu.addItem(info(floor))
        menu.addItem(.separator())

        // The proof: every rule, its number, the test and the points it gave.
        let proof = NSMenuItem(title: "Why this call - the proof", action: nil, keyEquivalent: "")
        let pm = NSMenu()
        for e in s.evidence {
            let it = NSMenuItem()
            let a = NSMutableAttributedString(string: "\(signed(e.points))   \(e.rule)\n",
                                              attributes: [.font: NSFont.boldSystemFont(ofSize: 13),
                                                           .foregroundColor: e.points > 0 ? signalColor("BUY") : e.points < 0 ? signalColor("SELL") : NSColor.labelColor])
            a.append(NSAttributedString(string: wrap(e.value, 70) + "\n",
                                        attributes: [.font: NSFont.menuFont(ofSize: 12), .foregroundColor: NSColor.labelColor]))
            a.append(NSAttributedString(string: wrap("Test: \(e.test)", 80) + "\n" + wrap("Source: \(e.source)", 80),
                                        attributes: [.font: NSFont.menuFont(ofSize: 11), .foregroundColor: NSColor.secondaryLabelColor]))
            it.attributedTitle = a
            it.toolTip = e.why
            it.isEnabled = false
            pm.addItem(it)
        }
        pm.addItem(.separator())
        pm.addItem(info("Total score \(signed(s.score)) → \(s.label)   (≥+3 strong buy · +1/+2 buy · 0 hold/wait · −1/−2 sell · ≤−3 strong sell)"))
        proof.submenu = pm
        menu.addItem(proof)

        let rec = NSMenuItem(title: "Has this worked before?", action: nil, keyEquivalent: "")
        let rm = NSMenu()
        let tr = l.track_record.summary
        func line(_ name: String, _ g: Latest.Group?, rising: Bool) {
            guard let g = g else { return }
            let hit = rising ? g.rose_pct : 100 - g.rose_pct
            rm.addItem(info("\(name) days (\(g.days)): price \(rising ? "higher" : "lower") 30 days later \(String(format: "%.0f", hit))% of the time, avg \(pc(g.avg_move_pct))"))
        }
        line("BUY", tr.buy_days, rising: true)
        if let g = tr.hold_days {
            rm.addItem(info("HOLD days (\(g.days)): keeping stock beat the holding cost \(String(format: "%.0f", g.beat_holding_cost_pct))% of the time, avg \(pc(g.avg_move_pct))"))
        }
        line("WAIT", tr.wait_days, rising: true)
        line("SELL", tr.sell_days, rising: false)
        if let all = l.track_record.summary_all, let h = all.hold_days, (tr.hold_days?.days ?? 0) < 10 {
            rm.addItem(info("HOLD since \(prettyDate(l.track_record.since ?? "")) (\(h.days) days): beat the holding cost \(String(format: "%.0f", h.beat_holding_cost_pct))% of the time, avg \(pc(h.avg_move_pct))"))
        }
        if let live = l.track_record.live {
            rm.addItem(.separator())
            rm.addItem(info(live.graded > 0
                ? "Live calls: \(live.graded) graded, right \(String(format: "%.0f", live.right_pct ?? 0))% of the time"
                : "Live calls: \(live.calls) logged - each is graded 30 days later"))
        }
        rm.addItem(info("Replayed over the last year using only the data known each day."))
        rec.submenu = rm
        menu.addItem(rec)

        let br = NSMenuItem(title: "Today's briefing", action: nil, keyEquivalent: "")
        let bm = NSMenu()
        bm.addItem(info(wrap(l.brief.english, 80)))
        bm.addItem(.separator())
        bm.addItem(info(wrap(l.brief.telugu, 70)))
        bm.addItem(.separator())
        bm.addItem(action("Copy English", #selector(copyEnglish)))
        bm.addItem(action("Copy తెలుగు", #selector(copyTelugu)))
        br.submenu = bm
        menu.addItem(br)

        let tm = l.timing
        menu.addItem(info("Usually cheapest \(tm.cheapest_months.joined(separator: " & ")) · dearest \(tm.dearest_months.joined(separator: " & "))"
                          + (tm.days_to_buy_window > 0 ? " · buy window in \(tm.days_to_buy_window) days" : " · in the buy window now")))
    }

    func settingsItem() -> NSMenuItem {
        let it = NSMenuItem(title: "Settings", action: nil, keyEquivalent: "")
        let m = NSMenu()
        // Menu bar
        m.addItem(groupHeader("Menu bar"))
        m.addItem(switchRow("Show price", Settings.showPrice, #selector(switchPrice(_:))))
        // Alerts
        m.addItem(.separator())
        m.addItem(groupHeader("Alerts"))
        m.addItem(switchRow("Notify on signal change / big moves", Settings.notify, #selector(switchNotify(_:))))
        m.addItem(segmentRow("Check every", ["15m", "30m", "1h", "2h"], [15, 30, 60, 120].firstIndex(of: Settings.minutes) ?? 1, #selector(segMinutes(_:))))
        // General
        m.addItem(.separator())
        m.addItem(groupHeader("General"))
        m.addItem(switchRow("Launch at login", SMAppService.mainApp.status == .enabled, #selector(switchLogin(_:))))
        m.addItem(segmentRow("Appearance", ["System", "Light", "Dark"], ["system", "light", "dark"].firstIndex(of: Settings.appearance) ?? 0, #selector(segAppearance(_:))))
        m.addItem(.separator())
        m.addItem(action("Data Source…", #selector(editSource)))
        it.submenu = m
        return it
    }

    // MARK: Settings rows (grouped, with switches and segmented controls)

    static let rowWidth: CGFloat = 300

    func groupHeader(_ title: String) -> NSMenuItem {
        let it = NSMenuItem()
        it.isEnabled = false
        it.attributedTitle = NSAttributedString(string: title.uppercased(), attributes: [
            .font: NSFont.systemFont(ofSize: 10, weight: .semibold),
            .foregroundColor: NSColor.secondaryLabelColor,
            .kern: 0.6])
        return it
    }

    func rowLabel(_ text: String) -> NSTextField {
        let l = NSTextField(labelWithString: text)
        l.font = .menuFont(ofSize: 13)
        l.textColor = .labelColor
        l.lineBreakMode = .byTruncatingTail
        return l
    }

    func switchRow(_ title: String, _ on: Bool, _ sel: Selector) -> NSMenuItem {
        let v = NSView(frame: NSRect(x: 0, y: 0, width: App.rowWidth, height: 30))
        let l = rowLabel(title); l.frame = NSRect(x: 14, y: 6, width: App.rowWidth - 82, height: 18)
        let sw = NSSwitch(); sw.controlSize = .small; sw.state = on ? .on : .off
        sw.target = self; sw.action = sel
        sw.sizeToFit(); sw.frame.origin = NSPoint(x: App.rowWidth - sw.frame.width - 14, y: (30 - sw.frame.height) / 2)
        v.addSubview(l); v.addSubview(sw)
        let it = NSMenuItem(); it.view = v
        return it
    }

    func segmentRow(_ title: String, _ labels: [String], _ selected: Int, _ sel: Selector) -> NSMenuItem {
        let v = NSView(frame: NSRect(x: 0, y: 0, width: App.rowWidth, height: 52))
        let l = rowLabel(title); l.frame = NSRect(x: 14, y: 31, width: App.rowWidth - 28, height: 16)
        let seg = NSSegmentedControl(labels: labels, trackingMode: .selectOne, target: self, action: sel)
        seg.controlSize = .small; seg.segmentStyle = .rounded; seg.selectedSegment = selected
        seg.frame = NSRect(x: 14, y: 5, width: App.rowWidth - 28, height: 22)
        v.addSubview(l); v.addSubview(seg)
        let it = NSMenuItem(); it.view = v
        return it
    }

    @objc func switchPrice(_ s: NSSwitch) { Settings.showPrice = s.state == .on; updateTitle() }
    @objc func switchNotify(_ s: NSSwitch) { Settings.notify = s.state == .on }
    @objc func switchLogin(_ s: NSSwitch) {
        toggleLogin()
        s.state = SMAppService.mainApp.status == .enabled ? .on : .off   // snap back if it failed
    }
    @objc func segMinutes(_ s: NSSegmentedControl) {
        let opts = [15, 30, 60, 120]
        guard opts.indices.contains(s.selectedSegment) else { return }
        Settings.minutes = opts[s.selectedSegment]; schedule()
    }
    @objc func segAppearance(_ s: NSSegmentedControl) {
        let opts = ["system", "light", "dark"]
        guard opts.indices.contains(s.selectedSegment) else { return }
        Settings.appearance = opts[s.selectedSegment]
        Settings.applyAppearance()
        dashboard.applyTheme()
    }

    func info(_ title: String) -> NSMenuItem {
        let it = NSMenuItem(title: title, action: nil, keyEquivalent: "")
        it.isEnabled = false
        return it
    }

    func action(_ title: String, _ sel: Selector, _ key: String = "") -> NSMenuItem {
        let it = NSMenuItem(title: title, action: sel, keyEquivalent: key)
        it.target = self
        return it
    }

    // MARK: Actions

    @objc func openDashboard() { dashboard.show() }
    @objc func openBrowser() { NSWorkspace.shared.open(Settings.siteURL) }
    @objc func openHelp() { NSWorkspace.shared.open(URL(string: repoURL + "/blob/main/guide/MAC_APP.md")!) }
    @objc func quit() { NSApp.terminate(nil) }

    @objc func copyEnglish() { copy(latest?.brief.english) }
    @objc func copyTelugu() { copy(latest?.brief.telugu) }
    func copy(_ s: String?) {
        guard let s = s else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(s + "\n" + Settings.siteURL.absoluteString, forType: .string)
    }

    @objc func toggleLogin() {
        do {
            if SMAppService.mainApp.status == .enabled { try SMAppService.mainApp.unregister() }
            else { try SMAppService.mainApp.register() }
        } catch {
            let a = NSAlert()
            a.messageText = "Couldn't change Launch at Login"
            a.informativeText = "\(error.localizedDescription)\n\nMove WheatWise to the Applications folder and try again, or add it in System Settings → General → Login Items."
            a.runModal()
        }
    }

    @objc func editSource() {
        let a = NSAlert()
        a.messageText = "Data source"
        a.informativeText = "The latest.json your WheatWise dashboard publishes. Change it only if you run your own copy (fork) of the repo."
        let f = NSTextField(frame: NSRect(x: 0, y: 0, width: 420, height: 24))
        f.stringValue = Settings.dataURL
        a.accessoryView = f
        a.addButton(withTitle: "Save")
        a.addButton(withTitle: "Cancel")
        a.addButton(withTitle: "Reset to Default")
        NSApp.activate(ignoringOtherApps: true)
        switch a.runModal() {
        case .alertFirstButtonReturn: Settings.dataURL = f.stringValue.trimmingCharacters(in: .whitespaces)
        case .alertThirdButtonReturn: Settings.d.removeObject(forKey: "dataURL")
        default: return
        }
        Settings.lastSignal = nil   // a different source shouldn't count as a signal change
        latest = nil
        refresh()
    }

    /// Menu-bar apps have no main menu, so ⌘C / ⌘V would not work in the dashboard's text fields.
    func installEditMenu() {
        let main = NSMenu()
        let appItem = NSMenuItem(); main.addItem(appItem)
        let am = NSMenu(); am.addItem(withTitle: "Close Window", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
        appItem.submenu = am
        let editItem = NSMenuItem(); main.addItem(editItem)
        let em = NSMenu(title: "Edit")
        em.addItem(withTitle: "Undo", action: Selector(("undo:")), keyEquivalent: "z")
        em.addItem(withTitle: "Redo", action: Selector(("redo:")), keyEquivalent: "Z")
        em.addItem(.separator())
        em.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        em.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        em.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        em.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editItem.submenu = em
        NSApp.mainMenu = main
    }
}

// MARK: - Dashboard window

/// The full dashboard in a window. Trades you enter here are kept in this app's own
/// web storage (separate from your browser) - use Export CSV / Import CSV to move them.
final class Dashboard: NSObject, NSWindowDelegate, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate {
    var window: NSWindow?
    var web: WKWebView?

    func show() {
        if window == nil {
            let cfg = WKWebViewConfiguration()
            cfg.websiteDataStore = .default()   // keeps trades (localStorage) between launches
            // Apply the Appearance choice before the page's own script reads its saved theme.
            cfg.userContentController.addUserScript(WKUserScript(source: Settings.themeScript, injectionTime: .atDocumentStart, forMainFrameOnly: true))
            let w = WKWebView(frame: .zero, configuration: cfg)
            w.navigationDelegate = self
            w.uiDelegate = self
            w.allowsBackForwardNavigationGestures = true
            let win = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1240, height: 860),
                               styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
            win.title = "WheatWise"
            win.contentView = w
            win.isReleasedWhenClosed = false
            win.delegate = self
            win.setFrameAutosaveName("WheatWiseDashboard")
            if !win.setFrameUsingName("WheatWiseDashboard") { win.center() }
            window = win
            web = w
            w.load(URLRequest(url: Settings.siteURL))
        } else if web?.url?.host != Settings.siteURL.host {
            web?.load(URLRequest(url: Settings.siteURL))
        } else {
            web?.reload()   // pick up the newest run
        }
        NSApp.setActivationPolicy(.regular)   // Dock icon + ⌘-Tab while the window is open
        NSApp.activate(ignoringOtherApps: true)
        window?.makeKeyAndOrderFront(nil)
    }

    /// Re-theme the open page at once (the script is re-read on every load, so it is always current).
    func applyTheme() {
        guard let w = web else { return }
        w.configuration.userContentController.removeAllUserScripts()
        w.configuration.userContentController.addUserScript(WKUserScript(source: Settings.themeScript, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        w.evaluateJavaScript(Settings.themeScript + ";if(typeof renderAll==='function'){try{renderAll()}catch(e){}}", completionHandler: nil)
    }

    func windowWillClose(_ n: Notification) { NSApp.setActivationPolicy(.accessory) }

    // Links that leave the dashboard (Help, GitHub, pib.gov.in…) open in the browser.
    func webView(_ w: WKWebView, decidePolicyFor a: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        if a.shouldPerformDownload { decisionHandler(.download); return }
        if let u = a.request.url, a.navigationType == .linkActivated, u.host != Settings.siteURL.host {
            NSWorkspace.shared.open(u)
            decisionHandler(.cancel)
            return
        }
        decisionHandler(.allow)
    }

    func webView(_ w: WKWebView, createWebViewWith c: WKWebViewConfiguration, for a: WKNavigationAction,
                 windowFeatures f: WKWindowFeatures) -> WKWebView? {
        if let u = a.request.url { NSWorkspace.shared.open(u) }   // target="_blank"
        return nil
    }

    func webView(_ w: WKWebView, navigationAction: WKNavigationAction, didBecome d: WKDownload) { d.delegate = self }
    func webView(_ w: WKWebView, navigationResponse: WKNavigationResponse, didBecome d: WKDownload) { d.delegate = self }

    // Export CSV
    func download(_ d: WKDownload, decideDestinationUsing r: URLResponse, suggestedFilename name: String,
                  completionHandler done: @escaping (URL?) -> Void) {
        let p = NSSavePanel()
        p.nameFieldStringValue = name
        p.directoryURL = FileManager.default.urls(for: .downloadsDirectory, in: .userDomainMask).first
        guard let win = window else { done(nil); return }
        p.beginSheetModal(for: win) { r in
            guard r == .OK, let u = p.url else { done(nil); return }
            try? FileManager.default.removeItem(at: u)
            done(u)
        }
    }

    // Import CSV
    func webView(_ w: WKWebView, runOpenPanelWith p: WKOpenPanelParameters, initiatedByFrame f: WKFrameInfo,
                 completionHandler done: @escaping ([URL]?) -> Void) {
        let o = NSOpenPanel()
        o.allowsMultipleSelection = p.allowsMultipleSelection
        o.canChooseDirectories = false
        guard let win = window else { done(nil); return }
        o.beginSheetModal(for: win) { r in done(r == .OK ? o.urls : nil) }
    }

    // alert() / confirm() from the page
    func webView(_ w: WKWebView, runJavaScriptAlertPanelWithMessage m: String, initiatedByFrame f: WKFrameInfo,
                 completionHandler done: @escaping () -> Void) {
        let a = NSAlert(); a.messageText = m
        a.runModal(); done()
    }

    func webView(_ w: WKWebView, runJavaScriptConfirmPanelWithMessage m: String, initiatedByFrame f: WKFrameInfo,
                 completionHandler done: @escaping (Bool) -> Void) {
        let a = NSAlert(); a.messageText = m
        a.addButton(withTitle: "OK"); a.addButton(withTitle: "Cancel")
        done(a.runModal() == .alertFirstButtonReturn)
    }
}

// MARK: - Main

let app = NSApplication.shared
let delegate = App()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()

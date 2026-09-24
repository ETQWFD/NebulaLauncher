/**
 * Nebula Launcher (Java) — 星云启动器 Java 版
 * 双击即用（需已安装 Java 8+，玩 MC 的机器通常都有）。
 * 功能：版本清单 / 原版+Fabric 安装 / 内存分配 / 优化 JVM 参数 / 启动后自动退出。
 * 零第三方依赖：内置轻量 JSON 解析器。
 */
import javax.swing.*;
import javax.swing.border.EmptyBorder;
import javax.swing.plaf.basic.BasicScrollBarUI;
import java.awt.*;
import java.awt.event.*;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.List;
import java.util.concurrent.*;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

public class NebulaLauncher {

    // ==================================================================
    // 常量
    // ==================================================================
    static final String APP_VERSION = "1.0.0";
    static final String[] MANIFEST_URLS = {
        "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json",
        "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json",
        "https://bmclapi2.bangbang93.com/mc/game/version_manifest_v2.json"
    };
    static final String FABRIC_META = "https://meta.fabricmc.net/v2";
    static final String[] JVM_FLAGS = {
        "-XX:+UseG1GC", "-XX:+ParallelRefProcEnabled", "-XX:MaxGCPauseMillis=200",
        "-XX:+UnlockExperimentalVMOptions", "-XX:+DisableExplicitGC", "-XX:+AlwaysPreTouch",
        "-XX:G1NewSizePercent=30", "-XX:G1MaxNewSizePercent=40", "-XX:G1HeapRegionSize=8M",
        "-XX:G1ReservePercent=20", "-XX:G1HeapWastePercent=5", "-XX:G1MixedGCCountTarget=4",
        "-XX:InitiatingHeapOccupancyPercent=15", "-XX:G1MixedGCLiveThresholdPercent=90",
        "-XX:G1RSetUpdatingPauseTimePercent=5", "-XX:SurvivorRatio=32", "-XX:+PerfDisableSharedMem",
        "-XX:MaxTenuringThreshold=1", "-XX:CompileThreshold=1500",
        "-Dusing.aikars.flags=https://mcflags.emc.gs", "-Daikars.new.flags=true",
        "-Dlog4j2.formatMsgNoLookups=true"
    };

    static File gameDir() {
        String os = System.getProperty("os.name").toLowerCase();
        if (os.contains("win")) return new File(System.getenv("APPDATA"), ".minecraft");
        if (os.contains("mac")) return new File(System.getProperty("user.home"), "Library/Application Support/minecraft");
        return new File(System.getProperty("user.home"), ".minecraft");
    }
    static String osName() {
        String os = System.getProperty("os.name").toLowerCase();
        return os.contains("win") ? "windows" : os.contains("mac") ? "osx" : "linux";
    }
    static String osArch() {
        String a = System.getProperty("os.arch").toLowerCase();
        return a.contains("64") || a.contains("aarch64") ? "64" : "32";
    }

    // ==================================================================
    // 极简 JSON 解析（仅支持对象/数组/字符串/数字/布尔/null）
    // ==================================================================
    static class Json {
        Object val;
        Json(Object v) { val = v; }
        Map<String, Json> obj() { return (Map<String, Json>) val; }
        List<Json> arr() { return (List<Json>) val; }
        boolean isObj() { return val instanceof Map; }
        boolean isArr() { return val instanceof List; }
        Json get(String key) { return isObj() ? obj().get(key) : null; }
        String str(String key) { Json j = get(key); return j == null ? null : String.valueOf(j.val); }
        String str() { return val == null ? null : String.valueOf(val); }
        int i(String key) { Json j = get(key); try { return j == null ? 0 : Integer.parseInt(String.valueOf(j.val)); } catch (Exception e) { return 0; } }

        static Json parse(String text) { return new Json(new P(text).parseValue()); }

        static class P {
            String s; int i = 0;
            P(String s) { this.s = s; }
            void ws() { while (i < s.length() && Character.isWhitespace(s.charAt(i))) i++; }
            Object parseValue() {
                ws();
                char c = s.charAt(i);
                if (c == '{') return parseObj();
                if (c == '[') return parseArr();
                if (c == '"') return parseStr();
                if (c == 't') { i += 4; return Boolean.TRUE; }
                if (c == 'f') { i += 5; return Boolean.FALSE; }
                if (c == 'n') { i += 4; return null; }
                return parseNum();
            }
            Map<String, Json> parseObj() {
                Map<String, Json> m = new LinkedHashMap<>();
                i++; ws();
                if (s.charAt(i) == '}') { i++; return m; }
                while (true) {
                    ws();
                    String key = parseStr();
                    ws();
                    i++; // :
                    m.put(key, new Json(parseValue()));
                    ws();
                    char c = s.charAt(i++);
                    if (c == '}') break;
                }
                return m;
            }
            List<Json> parseArr() {
                List<Json> l = new ArrayList<>();
                i++; ws();
                if (s.charAt(i) == ']') { i++; return l; }
                while (true) {
                    l.add(new Json(parseValue()));
                    ws();
                    char c = s.charAt(i++);
                    if (c == ']') break;
                }
                return l;
            }
            String parseStr() {
                i++; // "
                StringBuilder sb = new StringBuilder();
                while (i < s.length()) {
                    char c = s.charAt(i++);
                    if (c == '"') break;
                    if (c == '\\') {
                        char e = s.charAt(i++);
                        if (e == 'n') sb.append('\n');
                        else if (e == 't') sb.append('\t');
                        else if (e == 'u') sb.append((char) Integer.parseInt(s.substring(i, i + 4), 16));
                        else sb.append(e);
                        if (e == 'u') i += 4;
                    } else sb.append(c);
                }
                return sb.toString();
            }
            Object parseNum() {
                int start = i;
                while (i < s.length() && (Character.isDigit(s.charAt(i)) || "-+.eE".indexOf(s.charAt(i)) >= 0)) i++;
                String t = s.substring(start, i);
                try { return t.contains(".") || t.contains("e") ? (Object) Double.parseDouble(t) : (Object) Long.parseLong(t); }
                catch (Exception e) { return 0L; }
            }
        }
    }

    // ==================================================================
    // 网络与哈希
    // ==================================================================
    static byte[] get(String urlStr, int timeout) throws IOException {
        HttpURLConnection c = (HttpURLConnection) new URL(urlStr).openConnection();
        c.setConnectTimeout(timeout); c.setReadTimeout(timeout);
        c.setRequestProperty("User-Agent", "NebulaLauncher/1.0");
        if (c.getResponseCode() != 200) throw new IOException("HTTP " + c.getResponseCode() + " " + urlStr);
        try (InputStream in = c.getInputStream(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buf = new byte[65536];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            return out.toByteArray();
        } finally { c.disconnect(); }
    }

    static Json getJson(String url, int timeout) throws IOException {
        return Json.parse(new String(get(url, timeout), StandardCharsets.UTF_8));
    }

    static String sha1(byte[] data) throws Exception {
        MessageDigest md = MessageDigest.getInstance("SHA-1");
        byte[] d = md.digest(data);
        StringBuilder sb = new StringBuilder();
        for (byte b : d) sb.append(String.format("%02x", b));
        return sb.toString();
    }

    static boolean download(String url, File dest, String expectSha1) throws Exception {
        if (dest.exists() && expectSha1 != null && sha1(Files.readAllBytes(dest.toPath())).equals(expectSha1)) return true;
        File tmp = new File(dest.getParentFile(), dest.getName() + ".part");
        dest.getParentFile().mkdirs();
        byte[] data = get(url, 60000);
        if (expectSha1 != null && !sha1(data).equals(expectSha1)) throw new IOException("SHA1 校验失败 " + dest.getName());
        Files.write(tmp.toPath(), data);
        Files.move(tmp.toPath(), dest.toPath(), StandardCopyOption.REPLACE_EXISTING);
        return true;
    }

    static void unzip(byte[] data, File destDir) throws IOException {
        destDir.mkdirs();
        try (ZipInputStream z = new ZipInputStream(new ByteArrayInputStream(data))) {
            ZipEntry e;
            while ((e = z.getNextEntry()) != null) {
                File out = new File(destDir, e.getName());
                if (e.isDirectory()) { out.mkdirs(); continue; }
                out.getParentFile().mkdirs();
                try (OutputStream os = new FileOutputStream(out)) {
                    byte[] buf = new byte[65536];
                    int n;
                    while ((n = z.read(buf)) > 0) os.write(buf, 0, n);
                }
            }
        }
    }

    // ==================================================================
    // 启动器核心
    // ==================================================================
    static Json fetchManifest() throws Exception {
        Exception last = null;
        for (String u : MANIFEST_URLS) {
            try { return getJson(u, 20000); } catch (Exception e) { last = e; }
        }
        throw last != null ? last : new IOException("无法获取版本清单");
    }

    static Json fetchVersionJson(String url) throws Exception {
        return getJson(url, 30000);
    }

    static String javaPath() {
        return System.getProperty("java.home") + File.separator + "bin" + File.separator +
               (osName().equals("windows") ? "java.exe" : "java");
    }

    static String libraryPath(Json lib) {
        String name = lib.str("name");
        if (name == null) return "";
        Json dl = lib.get("downloads");
        if (dl != null && dl.get("artifact") != null && dl.get("artifact").str("path") != null)
            return dl.get("artifact").str("path");
        String[] p = name.split(":");
        if (p.length < 3) return name.replace('.', '/') + "/" + name + ".jar";
        String classifier = "";
        if (lib.get("natives") != null && lib.get("natives").str(osName()) != null) {
            classifier = lib.get("natives").str(osName()).replace("${arch}", osArch());
        }
        String base = p[0].replace('.', '/') + "/" + p[1] + "/" + p[2] + "/" + p[1] + "-" + p[2];
        return classifier.isEmpty() ? base + ".jar" : base + "-" + classifier + ".jar";
    }

    static boolean rulesOk(Json lib) {
        Json rules = lib.get("rules");
        if (rules == null) return true;
        boolean allowed = false;
        for (Json r : rules.arr()) {
            String action = r.str("action") == null ? "allow" : r.str("action");
            Json os = r.get("os");
            boolean match = true;
            if (os != null) {
                String name = os.str("name");
                if (name != null && !name.equals(osName())) match = false;
                String a = os.str("arch");
                if (a != null && !a.equals(osArch())) match = false;
            }
            if (match) allowed = action.equals("allow");
        }
        return allowed;
    }

    static String downloadAuthlib(File dir) throws Exception {
        File rt = new File(dir, "runtime"); rt.mkdirs();
        File jar = new File(rt, "authlib-injector.jar");
        if (jar.exists()) return jar.getPath();
        String url = null;
        try {
            String meta = new String(get("https://api.github.com/repos/yushijinhun/authlib-injector/releases/latest", 25000), StandardCharsets.UTF_8);
            Json assets = Json.parse(meta).get("assets");
            if (assets != null) {
                for (Json a : assets.arr()) {
                    if (a.str("name") != null && a.str("name").endsWith(".jar")) { url = a.str("browser_download_url"); break; }
                }
            }
        } catch (Exception ignored) {}
        if (url == null) url = "https://authlib-injector.yushi.moe/artifact/latest/authlib-injector.jar";
        download(url, jar, null);
        return jar.getPath();
    }

    static List<String> buildArgs(String mcDir, Json vdata, String vid, String username, int ramMb,
                                  String authlibFlag) throws Exception {
        String java = javaPath();
        String client = vdata.get("downloads").get("client").str("url");
        String mainClass = vdata.str("mainClass") == null ? "net.minecraft.client.main.Main" : vdata.str("mainClass");
        List<String> args = new ArrayList<>();
        args.add(java);
        args.add("-Xmx" + ramMb + "M");
        args.add("-Xms" + Math.max(ramMb / 4, 256) + "M");
        for (String f : JVM_FLAGS) args.add(f);
        if (authlibFlag != null && !authlibFlag.isEmpty()) args.add(authlibFlag);
        String natives = new File(mcDir, "versions/" + vid + "/natives").getPath();
        // classpath
        StringBuilder cp = new StringBuilder();
        String sep = File.pathSeparator;
        for (Json lib : vdata.get("libraries").arr()) {
            if (!rulesOk(lib)) continue;
            File f = new File(mcDir, "libraries/" + libraryPath(lib));
            if (f.exists() && f.getName().endsWith(".jar")) {
                if (cp.length() > 0) cp.append(sep);
                cp.append(f.getPath());
            }
        }
        File clientJar = new File(mcDir, "versions/" + vid + "/" + vid + ".jar");
        if (cp.length() > 0) cp.append(sep);
        cp.append(clientJar.getPath());
        String assetIndex = vdata.get("assetIndex") == null ? "legacy" : vdata.get("assetIndex").str("id");
        // arguments（兼容 1.13+ 与旧版）
        List<String> game = new ArrayList<>();
        Json arguments = vdata.get("arguments");
        if (arguments != null && arguments.isObj()) {
            for (Json a : arguments.get("game").arr()) {
                if (a.isObj()) {
                    if (rulesOk(a) && a.get("value") != null) {
                        if (a.get("value").isArr()) for (Json s : a.get("value").arr()) game.add(s.str());
                        else game.add(a.get("value").str());
                    }
                } else game.add(a.str());
            }
        } else if (vdata.str("minecraftArguments") != null) {
            for (String s : vdata.str("minecraftArguments").split(" ")) if (!s.isEmpty()) game.add(s);
        }
        Map<String, String> tokens = new HashMap<>();
        tokens.put("auth_player_name", username);
        tokens.put("version_name", vid);
        tokens.put("game_directory", mcDir);
        tokens.put("assets_root", new File(mcDir, "assets").getPath());
        tokens.put("assets_index_name", assetIndex);
        tokens.put("auth_uuid", UUID.nameUUIDFromBytes(("OfflinePlayer:" + username).getBytes()).toString().replace("-", ""));
        tokens.put("auth_access_token", "0");
        tokens.put("clientid", "NebulaLauncher");
        tokens.put("auth_xuid", "0");
        tokens.put("user_type", "legacy");
        tokens.put("version_type", vdata.str("type") == null ? "release" : vdata.str("type"));
        tokens.put("user_properties", "{}");
        tokens.put("resolution_width", "854");
        tokens.put("resolution_height", "480");
        tokens.put("natives_directory", natives);
        tokens.put("launcher_name", "NebulaLauncher");
        tokens.put("launcher_version", APP_VERSION);
        tokens.put("classpath", cp.toString());
        tokens.put("classpath_separator", sep);
        args.add("-Djava.library.path=" + natives);
        args.add("-cp"); args.add(cp.toString());
        args.add(mainClass);
        for (String g : game) {
            String t = g;
            for (Map.Entry<String, String> e : tokens.entrySet()) t = t.replace("${" + e.getKey() + "}", e.getValue());
            if (!t.contains("${")) args.add(t);
        }
        return args;
    }

    // ==================================================================
    // Swing 界面
    // ==================================================================
    static final Color BG = new Color(18, 21, 29);
    static final Color CARD = new Color(30, 36, 50);
    static final Color BLUE = new Color(61, 139, 255);
    static final Color TEXT = new Color(234, 240, 255);
    static final Color DIM = new Color(138, 147, 168);

    static Map<String, String> zh = new HashMap<>();
    static Map<String, String> en = new HashMap<>();
    static { zhPut(); enPut(); }

    static void zhPut() {
        zh.put("title", "星云启动器"); zh.put("version", "版本"); zh.put("memory", "内存分配");
        zh.put("account", "游戏账号"); zh.put("launch", "启动游戏"); zh.put("refresh", "刷新");
        zh.put("install", "安装版本"); zh.put("status_wait", "就绪，点击启动"); zh.put("installing", "正在安装…");
        zh.put("installed", "安装完成"); zh.put("launching", "正在启动…"); zh.put("done", "游戏已启动，启动器即将关闭");
        zh.put("nover", "请先安装一个版本"); zh.put("inst", "安装"); zh.put("vanilla", "原版");
        zh.put("fabric", "Fabric"); zh.put("lang", "语言"); zh.put("gb", "GB");
    }
    static void enPut() {
        en.put("title", "Nebula Launcher"); en.put("version", "Version"); en.put("memory", "Memory (RAM)");
        en.put("account", "Account"); en.put("launch", "Launch Game"); en.put("refresh", "Refresh");
        en.put("install", "Install"); en.put("status_wait", "Ready, click launch"); en.put("installing", "Installing…");
        en.put("installed", "Installed"); en.put("launching", "Launching…"); en.put("done", "Game started, launcher will close");
        en.put("nover", "Install a version first"); en.put("inst", "Install"); en.put("vanilla", "Vanilla");
        en.put("fabric", "Fabric"); en.put("lang", "Language"); en.put("gb", "GB");
    }
    static String tr(Map<String, String> lang, String key) { return lang.getOrDefault(key, key); }

    public static void main(String[] args) throws Exception {
        try {
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        } catch (Exception ignored) {}
        SwingUtilities.invokeLater(NebulaLauncher::showUI);
    }

    static void showUI() {
        JFrame frame = new JFrame("Nebula Launcher · 星云启动器");
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setSize(980, 640);
        frame.setMinimumSize(new Dimension(860, 560));
        frame.setLocationRelativeTo(null);
        try { frame.setIconImage(Toolkit.getDefaultToolkit().getImage(NebulaLauncher.class.getResource("/icon.png"))); } catch (Exception ignored) {}

        Map<String, String> lang = zh;
        JComboBox<String> langBox = new JComboBox<>(new String[]{"简体中文", "English"});

        JList<String> versionList = new JList<>();
        DefaultListModel<String> vm = new DefaultListModel<>();
        versionList.setModel(vm);
        JLabel status = new JLabel(" ");
        JProgressBar bar = new JProgressBar();
        bar.setStringPainted(false);
        JSlider ram = new JSlider(1024, 16384, 4096);
        ram.setMajorTickSpacing(4096); ram.setMinorTickSpacing(1024);
        ram.setPaintTicks(true);
        JLabel ramLabel = new JLabel("4.0 GB (4096 MB)");
        JTextField nameField = new JTextField("Steve", 16);
        JButton launchBtn = new JButton("启动游戏");
        JButton refreshBtn = new JButton("刷新");
        JButton installBtn = new JButton("安装版本");

        // ---- 样式 ----
        frame.getContentPane().setBackground(BG);
        Font uiFont = new Font("Microsoft YaHei", Font.PLAIN, 14);
        frame.setFont(uiFont);
        styleList(versionList);
        styleBtn(refreshBtn); styleBtn(installBtn);
        styleBtnPrimary(launchBtn);
        styleField(nameField); styleField(ram);
        status.setForeground(DIM);
        ramLabel.setForeground(DIM);
        langBox.setBackground(CARD); langBox.setForeground(TEXT);
        ram.setBackground(BG); ram.setForeground(BLUE);

        // ---- 布局 ----
        JPanel root = new JPanel(new BorderLayout(0, 0));
        root.setBackground(BG);
        root.setBorder(new EmptyBorder(18, 20, 18, 20));

        // 左侧：版本
        JPanel left = new JPanel(new BorderLayout(8, 8));
        left.setBackground(CARD); left.setBorder(BorderFactory.createLineBorder(new Color(42, 50, 71), 1));
        left.setPreferredSize(new Dimension(280, 0));
        JLabel vTitle = new JLabel("版本管理"); vTitle.setForeground(TEXT); vTitle.setFont(uiFont.deriveFont(Font.BOLD, 16));
        JPanel leftTop = new JPanel(new BorderLayout()); leftTop.setOpaque(false);
        leftTop.add(vTitle, BorderLayout.CENTER);
        JPanel refreshWrap = new JPanel(new FlowLayout(FlowLayout.RIGHT, 0, 0)); refreshWrap.setOpaque(false);
        refreshWrap.add(refreshBtn); leftTop.add(refreshWrap, BorderLayout.EAST);
        left.add(leftTop, BorderLayout.NORTH);
        left.add(new JScrollPane(versionList), BorderLayout.CENTER);
        JPanel instWrap = new JPanel(new BorderLayout()); instWrap.setOpaque(false);
        instWrap.add(installBtn, BorderLayout.CENTER);
        left.add(instWrap, BorderLayout.SOUTH);

        // 右侧：启动
        JPanel right = new JPanel(new GridBagLayout());
        right.setBackground(BG);
        GridBagConstraints g = new GridBagConstraints();
        g.insets = new Insets(10, 6, 10, 6);
        g.fill = GridBagConstraints.HORIZONTAL;

        JLabel rTitle = new JLabel("启动游戏"); rTitle.setForeground(TEXT); rTitle.setFont(uiFont.deriveFont(Font.BOLD, 26));
        g.gridx = 0; g.gridy = 0; g.gridwidth = 2; right.add(rTitle, g);

        JLabel mTitle = new JLabel("内存分配"); mTitle.setForeground(DIM);
        g.gridy = 1; g.gridwidth = 1; g.anchor = GridBagConstraints.WEST; right.add(mTitle, g);
        g.gridy = 2; g.gridwidth = 2; right.add(ram, g);
        g.gridy = 3; g.anchor = GridBagConstraints.CENTER; right.add(ramLabel, g);

        JLabel aTitle = new JLabel("游戏账号"); aTitle.setForeground(DIM);
        g.gridy = 4; g.gridwidth = 1; g.anchor = GridBagConstraints.WEST; right.add(aTitle, g);
        JComboBox<String> acctBox = new JComboBox<>(new String[]{"离线账号", "自定义服务器"});
        acctBox.setBackground(CARD); acctBox.setForeground(TEXT);
        g.gridy = 4; g.gridx = 1; g.gridwidth = 1; g.anchor = GridBagConstraints.CENTER; right.add(acctBox, g);
        g.gridy = 5; g.gridx = 0; g.gridwidth = 2; g.anchor = GridBagConstraints.CENTER; right.add(nameField, g);
        JTextField serverField = new JTextField();
        serverField.setBackground(CARD); serverField.setForeground(TEXT); serverField.setCaretColor(TEXT);
        serverField.setToolTipText("authlib 服务器地址，如 https://example.com/api/authlib-injector");
        serverField.setVisible(false);
        g.gridy = 6; g.gridwidth = 2; right.add(serverField, g);
        JPasswordField pwdField = new JPasswordField();
        pwdField.setBackground(CARD); pwdField.setForeground(TEXT); pwdField.setCaretColor(TEXT);
        pwdField.setToolTipText("服务器账号密码");
        pwdField.setVisible(false);
        g.gridy = 7; g.gridwidth = 2; right.add(pwdField, g);

        acctBox.addActionListener(e -> {
            boolean custom = acctBox.getSelectedIndex() == 1;
            serverField.setVisible(custom);
            pwdField.setVisible(custom);
            frame.pack();
        });

        g.gridy = 8; g.gridwidth = 2; g.ipady = 14;
        right.add(launchBtn, g);
        g.ipady = 0;
        g.gridy = 9; right.add(status, g);
        g.gridy = 10; g.fill = GridBagConstraints.HORIZONTAL; right.add(bar, g);

        // 底部：语言
        JPanel bottom = new JPanel(new BorderLayout()); bottom.setOpaque(false);
        bottom.add(langBox, BorderLayout.EAST);

        root.add(left, BorderLayout.WEST);
        root.add(right, BorderLayout.CENTER);
        root.add(bottom, BorderLayout.SOUTH);
        frame.setContentPane(root);

        Runnable applyLang = () -> {
            boolean zhMode = langBox.getSelectedIndex() == 0;
            Map<String, String> L = zhMode ? zh : en;
            frame.setTitle(tr(L, "title") + (zhMode ? " · Nebula Launcher" : " · 星云启动器"));
            vTitle.setText(tr(L, "version"));
            mTitle.setText(tr(L, "memory"));
            aTitle.setText(tr(L, "account"));
            launchBtn.setText(tr(L, "launch"));
            refreshBtn.setText(tr(L, "refresh"));
            installBtn.setText(tr(L, "install"));
            rTitle.setText(tr(L, "title").equals("Nebula Launcher") ? "Launch" : "启动游戏");
            if (status.getText().isEmpty() || status.getText().equals(tr(en, "status_wait")) || status.getText().equals(tr(zh, "status_wait")))
                status.setText(tr(L, "status_wait"));
            langBox.setSelectedIndex(zhMode ? 0 : 1);
        };

        // ---- 数据加载 ----
        Runnable loadVersions = () -> {
            File vdir = new File(gameDir(), "versions");
            vm.clear();
            if (vdir.isDirectory()) {
                String[] list = vdir.list();
                if (list != null) { Arrays.sort(list, Collections.reverseOrder()); for (String s : list) vm.addElement(s); }
            }
            if (vm.isEmpty()) vm.addElement(tr(langBox.getSelectedIndex() == 0 ? zh : en, "nover"));
        };

        refreshBtn.addActionListener(e -> loadVersions.run());
        langBox.addActionListener(e -> applyLang.run());
        applyLang.run();
        loadVersions.run();

        // ---- 安装 ----
        installBtn.addActionListener(e -> {
            installBtn.setEnabled(false);
            status.setText(tr(lang, "installing"));
            new Thread(() -> {
                try {
                    Json manifest = fetchManifest();
                    String latest = "";
                    Json vi = null;
                    for (Json v : manifest.get("versions").arr()) {
                        if (vi == null && "release".equals(v.str("type"))) { latest = v.str("id"); vi = v; }
                    }
                    if (vi == null) throw new IOException("无可用版本");
                    final String fLatest = latest;
                    final Json fVi = vi;
                    Json vdata = fetchVersionJson(fVi.str("url"));
                    File dir = gameDir();
                    File vdir = new File(dir, "versions/" + fLatest);
                    vdir.mkdirs();
                    // client jar
                    String cUrl = vdata.get("downloads").get("client").str("url");
                    File cj = new File(vdir, fLatest + ".jar");
                    download(cUrl, cj, vdata.get("downloads").get("client").str("sha1"));
                    // 保存版本 json
                    Files.write(new File(vdir, fLatest + ".json").toPath(),
                            new String(get(vi.str("url"), 30000), StandardCharsets.UTF_8).getBytes(StandardCharsets.UTF_8));
                    // libraries
                    List<Json> libs = vdata.get("libraries").arr();
                    ExecutorService pool = Executors.newFixedThreadPool(8);
                    List<Future<?>> futures = new ArrayList<>();
                    for (Json lib : libs) {
                        if (!rulesOk(lib)) continue;
                        String path = libraryPath(lib);
                        if (path.isEmpty()) continue;
                        Json art = lib.get("downloads") != null ? lib.get("downloads").get("artifact") : null;
                        String url = art != null ? art.str("url") : null;
                        String sha = art != null ? art.str("sha1") : null;
                        if (url == null) url = "https://libraries.minecraft.net/" + path;
                        final String fu = url, fsha = sha;
                        File dest = new File(dir, "libraries/" + path);
                        futures.add(pool.submit(() -> { try { download(fu, dest, fsha); return null; } catch (Exception ex) { return ex; } }));
                    }
                    int done = 0;
                    for (Future<?> f : futures) { f.get(); done++; bar.setValue((int) (done * 100.0 / futures.size())); }
                    pool.shutdown();
                    // natives
                    for (Json lib : libs) {
                        if (lib.get("natives") == null || !rulesOk(lib)) continue;
                        File njar = new File(dir, "libraries/" + libraryPath(lib));
                        if (njar.exists()) unzip(Files.readAllBytes(njar.toPath()), new File(vdir, "natives"));
                    }
                    SwingUtilities.invokeLater(() -> {
                        status.setText(tr(lang, "installed") + ": " + fLatest);
                        installBtn.setEnabled(true);
                        loadVersions.run();
                    });
                } catch (Exception ex) {
                    SwingUtilities.invokeLater(() -> { status.setText("Error: " + ex.getMessage()); installBtn.setEnabled(true); });
                }
            }).start();
        });

        // ---- 启动 ----
        launchBtn.addActionListener(e -> {
            String vid = versionList.getSelectedValue();
            if (vid == null || vm.isEmpty() || vm.get(0).equals(tr(lang, "nover"))) {
                status.setText(tr(lang, "nover"));
                return;
            }
            File dir = gameDir();
            File vj = new File(dir, "versions/" + vid + "/" + vid + ".json");
            if (!vj.exists()) { status.setText("Version JSON missing"); return; }
            String username = nameField.getText().trim().isEmpty() ? "Steve" : nameField.getText().trim();
            int ramMb = ram.getValue();
            final String authlibFlag;
            if (acctBox.getSelectedIndex() == 1) {
                String server = serverField.getText().trim();
                String pwd = new String(pwdField.getPassword()).trim();
                if (server.isEmpty() || pwd.isEmpty() || username.isEmpty()) {
                    status.setText("请填写服务器地址、账号与密码");
                    return;
                }
                try {
                    String jar = downloadAuthlib(dir);
                    authlibFlag = "-javaagent:" + jar + "=" + server;
                    status.setText("自定义服务器模式 · authlib-injector 就绪");
                } catch (Exception ex) {
                    status.setText("authlib 下载失败: " + ex.getMessage());
                    return;
                }
            } else {
                authlibFlag = null;
            }
            launchBtn.setEnabled(false);
            status.setText(tr(lang, "launching"));
            new Thread(() -> {
                try {
                    Json vdata = Json.parse(new String(Files.readAllBytes(vj.toPath()), StandardCharsets.UTF_8));
                    List<String> cmd = buildArgs(dir.getPath(), vdata, vid, username, ramMb, authlibFlag);
                    // 日志
                    File logDir = new File(dir, "logs"); logDir.mkdirs();
                    ProcessBuilder pb = new ProcessBuilder(cmd);
                    pb.directory(dir);
                    pb.redirectErrorStream(true);
                    Process proc = pb.start();
                    try (BufferedReader br = new BufferedReader(new InputStreamReader(proc.getInputStream()))) {
                        String line;
                        while (proc.isAlive() && (line = br.readLine()) != null) {
                            if (line.toLowerCase().contains("exception") || line.toLowerCase().contains("error")) {
                                System.out.println("[MC] " + line);
                            }
                        }
                    }
                    // 等待游戏存活几秒再退出启动器
                    Thread.sleep(4000);
                    if (proc.isAlive()) {
                        SwingUtilities.invokeLater(() -> {
                            status.setText(tr(lang, "done"));
                            try { Thread.sleep(1200); } catch (Exception ignored) {}
                            System.exit(0);
                        });
                    } else {
                        SwingUtilities.invokeLater(() -> { status.setText("Game exited early. See logs."); launchBtn.setEnabled(true); });
                    }
                } catch (Exception ex) {
                    SwingUtilities.invokeLater(() -> { status.setText("Error: " + ex.getMessage()); launchBtn.setEnabled(true); });
                }
            }).start();
        });

        frame.setVisible(true);
    }

    static void styleList(JList<String> list) {
        list.setBackground(CARD); list.setForeground(TEXT);
        list.setSelectionBackground(new Color(40, 60, 90));
        list.setSelectionForeground(Color.WHITE);
        list.setFont(new Font("Microsoft YaHei", Font.PLAIN, 14));
        list.setBorder(new EmptyBorder(6, 6, 6, 6));
    }
    static void styleBtn(JButton b) {
        b.setBackground(new Color(24, 32, 48)); b.setForeground(BLUE);
        b.setFocusPainted(false); b.setBorder(BorderFactory.createLineBorder(new Color(61, 139, 255, 90), 1));
        b.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
    }
    static void styleBtnPrimary(JButton b) {
        b.setBackground(new Color(61, 139, 255)); b.setForeground(Color.WHITE);
        b.setFocusPainted(false); b.setBorderPainted(false);
        b.setFont(b.getFont().deriveFont(Font.BOLD, 17));
        b.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
    }
    static void styleField(JComponent c) {
        c.setBackground(new Color(20, 25, 38)); c.setForeground(TEXT);
        c.setBorder(BorderFactory.createLineBorder(new Color(42, 50, 71), 1));
    }
}

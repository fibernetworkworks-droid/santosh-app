// W2b of the Platforms plan: the PowerToys Run door for Hoola.
// Alt+Space, type 'hoola', Enter - Hoola Desktop opens.
// W3 of the Platforms plan: type 'hoola <sawaal>' and the sawaal rides the PC->Hoola TEXT LANE -
// the plugin hands the words to Hoola Desktop with --ask, the desktop sends them into her
// conversation (POST /api/pc/quickask with its own paired token) and Hoola answers there.
// The launch still goes through the SAME user-level App Paths alias the Win+R MVP (W2a) created
// (HKCU\Software\Microsoft\Windows\CurrentVersion\App Paths\hoola.exe), so this PC has
// exactly ONE launch truth and nothing else to configure. If the alias is missing the
// plugin says so instead of guessing paths - the desktop app owns that switch.
using System.Diagnostics;
using Microsoft.Win32;
using ManagedCommon;
using Wox.Plugin;
using Wox.Plugin.Logger;

namespace Community.PowerToys.Run.Plugin.Hoola
{
    /// <summary>PowerToys Run se 'hoola' - Hoola Desktop khulta hai (W2a ke App Paths alias se).</summary>
    public class Main : IPlugin, IDisposable
    {
        /// <summary>ID of the plugin (32 hex digits, matches plugin.json - never changes).</summary>
        public static string PluginID => "162E72D3C1D7464E865293A276993A7B";

        public string Name => "Hoola";

        public string Description => "Hoola Desktop khologiye - 'hoola' likhiye, Enter dabaiye";

        private PluginInitContext? Context { get; set; }

        private string? IconPath { get; set; }

        private bool Disposed { get; set; }

        public void Init(PluginInitContext context)
        {
            Context = context ?? throw new ArgumentNullException(nameof(context));
            Context.API.ThemeChanged += OnThemeChanged;
            UpdateIconPath(Context.API.GetCurrentTheme());
        }

        public List<Result> Query(Query query)
        {
            var q = (query.Search ?? string.Empty).Trim();
            Log.Info($"Query: '{q}'", GetType());
            return new List<Result>
            {
                new Result
                {
                    QueryTextDisplay = q,
                    IcoPath = IconPath,
                    Title = q.Length == 0 ? "Hoola Desktop kholo" : $"Hoola se poochho: {q}",
                    SubTitle = q.Length == 0
                        ? "Hoola Desktop khulta hai - kaam wahan se, phone par Hoola ke saath"
                        : "Sawaal Hoola ki conversation mein jaata hai - jawab phone / console par",
                    Score = 100,
                    Action = _ => q.Length == 0 ? Launch() : LaunchAsk(q),
                },
            };
        }

        /// <summary>Open Hoola Desktop through the W2a alias - one launch truth on this PC.</summary>
        private bool Launch()
        {
            var exe = AliasExe();
            if (exe is null)
            {
                Log.Warn("App Paths alias 'hoola.exe' not found", GetType());
                Context?.API.ShowMsg("Hoola",
                    "Pehle Hoola Desktop khologiye aur 'Win+R alias' on kijiye - wahi 'hoola' alias " +
                    "PowerToys Run ka raasta bhi hai. (Phone > Mera PC se kahein: 'Win+R se hoola khulwao'.)");
                return false;
            }
            try
            {
                Process.Start(new ProcessStartInfo(exe) { UseShellExecute = true });
                return true;
            }
            catch (Exception e)
            {
                Log.Exception("Launch failed", e, GetType());
                Context?.API.ShowMsg("Hoola", $"Hoola Desktop nahi khula: {e.Message}");
                return false;
            }
        }

        /// <summary>W3 text lane: hand the typed sawaal to Hoola Desktop with --ask; the desktop
        /// sends it into her conversation through the quick-ask lane (its own paired token).</summary>
        private bool LaunchAsk(string ask)
        {
            var exe = AliasExe();
            if (exe is null)
            {
                Log.Warn("App Paths alias 'hoola.exe' not found for --ask", GetType());
                Context?.API.ShowMsg("Hoola",
                    "Pehle Hoola Desktop khologiye aur 'Win+R alias' on kijiye - wahi 'hoola' alias " +
                    "PowerToys Run ka raasta bhi hai.");
                return false;
            }
            try
            {
                Process.Start(new ProcessStartInfo(exe)
                {
                    UseShellExecute = true,
                    Arguments = "--ask " + QuoteArg(ask),
                });
                return true;
            }
            catch (Exception e)
            {
                Log.Exception("Ask launch failed", e, GetType());
                Context?.API.ShowMsg("Hoola", $"Sawaal nahi bheja ja saka: {e.Message}");
                return false;
            }
        }

        /// <summary>Windows command-line quoting: wrap in quotes, double the embedded ones.</summary>
        internal static string QuoteArg(string arg) => '"' + arg.Replace("\"", "\"\"") + '"';

        /// <summary>The full SantoshDesktop.exe path from the W2a alias, or null when it is not set.</summary>
        internal static string? AliasExe()
        {
            try
            {
                using var k = Registry.CurrentUser.OpenSubKey(
                    @"Software\Microsoft\Windows\CurrentVersion\App Paths\hoola.exe");
                var v = k?.GetValue(null) as string;   // the (Default) value: "C:\...\SantoshDesktop.exe"
                if (string.IsNullOrWhiteSpace(v))
                {
                    return null;
                }
                v = v.Trim().Trim('"');
                return File.Exists(v) ? v : null;
            }
            catch (Exception e)
            {
                Log.Warn($"Alias read failed: {e.Message}", GetType());
                return null;
            }
        }

        private void UpdateIconPath(Theme theme) =>
            IconPath = theme == Theme.Light || theme == Theme.HighContrastWhite
                ? Context?.CurrentPluginMetadata.IcoPathLight
                : Context?.CurrentPluginMetadata.IcoPathDark;

        private void OnThemeChanged(Theme oldTheme, Theme newTheme) => UpdateIconPath(newTheme);

        public void Dispose()
        {
            if (Disposed)
            {
                return;
            }
            if (Context?.API != null)
            {
                Context.API.ThemeChanged -= OnThemeChanged;
            }
            Disposed = true;
            GC.SuppressFinalize(this);
        }
    }
}

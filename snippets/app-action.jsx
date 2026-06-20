// app-action.jsx — Saturday docs reusable snippet.
// Makes a doc instruction clickable so a coach lands in the actual Saturday app.
// Mobile: a normal-looking bold link that the OS hands to the app (universal link).
// Desktop: an identically-styled inline button that pops a "scan to open on phone" QR modal.
//
// Mintlify sandbox constraints honored here:
//   - React hooks (useState/useEffect) are PRE-INJECTED — no React import.
//   - No external npm packages — the QR is a remote image endpoint, not a qr library.
//   - Named export only, no default export, no cross-snippet imports.
//   - navigator.* is browser-only — touched solely inside useEffect (undefined during SSR).

// AppAction: clickable instruction that opens the Saturday app for the destination `path`.
// NOTE: Mintlify evaluates the EXPORTED component in isolation — a module-scope sibling
// (a top-level `const LINK_STYLE`) is NOT in scope at render time and throws
// "ReferenceError: LINK_STYLE is not defined", rendering the component empty. So every
// value the component needs lives INSIDE the function body; only the pre-injected hooks
// (useState/useEffect) come from outside.
export const AppAction = ({ path = "/open-app", children }) => {
  // Shared inline style so the mobile link and the desktop button read IDENTICALLY
  // inside a sentence: bold, brand teal, subtle underline that strengthens on hover.
  const LINK_STYLE = {
    fontWeight: 600,            // semibold — reads as a strong doc link
    color: "#1aabb8",           // Saturday brand teal
    cursor: "pointer",
    textDecoration: "underline",
    textDecorationColor: "rgba(26, 171, 184, 0.4)", // subtle underline at rest
    textUnderlineOffset: "2px",
    background: "none",
    border: "none",
    padding: 0,
    font: "inherit",            // inherit surrounding prose font so it sits in-line
  };

  // Universal/deep link the OS resolves to the installed app (or the web fallback).
  const deepUrl = "https://saturday.fit" + path;

  // isMobile starts false so the FIRST (server) render is always the desktop branch —
  // this keeps SSR from ever touching navigator and avoids a hydration mismatch crash.
  const [isMobile, setIsMobile] = useState(false);
  const [showQR, setShowQR] = useState(false);

  // Device sniff runs ONLY in the browser, after mount — navigator is safe here.
  useEffect(() => {
    setIsMobile(/iPhone|iPad|iPod|Android/i.test(navigator.userAgent));
  }, []);

  // Hover handlers strengthen the underline so it feels like a live link.
  const onEnter = (e) => {
    e.currentTarget.style.textDecorationColor = "#1aabb8";
  };
  const onLeave = (e) => {
    e.currentTarget.style.textDecorationColor = "rgba(26, 171, 184, 0.4)";
  };

  // MOBILE — render a real anchor; tapping lets the OS open the Saturday app.
  if (isMobile) {
    return (
      <a
        href={deepUrl}
        style={LINK_STYLE}
        onMouseEnter={onEnter}
        onMouseLeave={onLeave}
      >
        {children}
      </a>
    );
  }

  // Remote QR image endpoint encoding the deep link (no qr npm package needed).
  const qrSrc =
    "https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=" +
    encodeURIComponent(deepUrl);

  // DESKTOP — an inline button styled exactly like the mobile link; opens the QR modal.
  return (
    <>
      <button
        type="button"
        onClick={() => setShowQR(true)}
        style={LINK_STYLE}
        onMouseEnter={onEnter}
        onMouseLeave={onLeave}
      >
        {children}
      </button>

      {/* Modal: dark translucent overlay + centered card. Dismiss via overlay or Close. */}
      {showQR && (
        <div
          onClick={() => setShowQR(false)}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 9999,
            background: "rgba(0, 0, 0, 0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "1rem",
          }}
        >
          {/* Stop propagation so clicks INSIDE the card don't dismiss the modal. */}
          <div
            onClick={(e) => e.stopPropagation()}
            className="not-prose"
            style={{
              background: "#ffffff",
              borderRadius: "16px",
              padding: "1.5rem",
              maxWidth: "320px",
              width: "100%",
              textAlign: "center",
              boxShadow: "0 20px 60px rgba(0, 0, 0, 0.35)",
            }}
          >
            <p
              style={{
                margin: "0 0 1rem",
                fontWeight: 600,
                color: "#11181c",
                fontSize: "0.95rem",
              }}
            >
              Scan with your phone to open the Saturday app
            </p>

            <img
              src={qrSrc}
              width={220}
              height={220}
              alt={"QR code to open " + deepUrl + " in the Saturday app"}
              style={{ display: "block", margin: "0 auto", borderRadius: "8px" }}
            />

            {/* Fallback link in case the QR image service is unavailable. */}
            <a
              href={deepUrl}
              style={{
                display: "inline-block",
                marginTop: "1rem",
                color: "#1aabb8",
                fontWeight: 600,
                fontSize: "0.8rem",
                wordBreak: "break-all",
              }}
            >
              {deepUrl}
            </a>

            {/* Explicit Close button — second way to dismiss the modal. */}
            <button
              type="button"
              onClick={() => setShowQR(false)}
              style={{
                display: "block",
                width: "100%",
                marginTop: "1.25rem",
                padding: "0.6rem",
                borderRadius: "10px",
                border: "none",
                background: "#1aabb8",
                color: "#ffffff",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );
};

/**
 * Root page — serves the Webflow landing page in a full-screen iframe.
 * "Product Tour" button inside the iframe navigates the parent to /sourcing.
 */

export default function LandingPage() {
    return (
        <iframe
            src="/landing.html"
            style={{
                position: "fixed",
                top: 0,
                left: 0,
                width: "100%",
                height: "100%",
                border: "none",
                margin: 0,
                padding: 0,
            }}
            title="IPM Engine — Landing Page"
        />
    );
}

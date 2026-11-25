// Google Analytics 4 (GA4) Consent Mode and Tracking Initialization
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('consent', 'default', {
  'analytics_storage': localStorage.getItem('transify_cookie_consent') === 'accepted' ? 'granted' : 'denied',
  'ad_storage': 'denied'
});
gtag('config', 'G-TRANSIFY20', {
  'send_page_view': false
});

import { Link } from 'react-router-dom';

const Footer = () => (
  <footer className="border-t border-line bg-paper">
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-5 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between sm:px-7">
      <div>
        <div className="mb-1 font-semibold text-ink">BoilerSnipe</div>
        <div>Free and independent. Not affiliated with Purdue University.</div>
      </div>
      <div className="flex flex-wrap gap-x-6 gap-y-3">
        <Link to="/about" className="hover:text-ink">About &amp; transparency</Link>
        <Link to="/privacy" className="hover:text-ink">Privacy</Link>
        <Link to="/terms" className="hover:text-ink">Terms</Link>
        <a href="mailto:contact@boilersnipe.com" className="hover:text-ink">Contact</a>
      </div>
    </div>
  </footer>
);

export default Footer;

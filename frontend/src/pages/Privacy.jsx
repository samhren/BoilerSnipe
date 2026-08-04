import { Link } from 'react-router-dom';

const Privacy = () => {
  return (
    <div className="page-shell">
      <div className="mx-auto max-w-3xl px-5 py-12 sm:px-7 sm:py-16">
        <p className="eyebrow mb-3">The plain-language version</p>
        <h1 className="display-title mb-9">Privacy policy</h1>

        <div className="legal-copy space-y-7 border-t border-line pt-7">
          <p className="text-sm text-slate-500">Last updated: July 2026</p>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">1. Information We Collect</h2>
            <p className="mb-2">We collect information you provide directly:</p>
            <ul className="list-disc list-outside space-y-1 pl-5">
              <li><strong>Account Information:</strong> Your email address, plus a password if you register with one. If you use "Sign in with Google," we receive your email address from Google and never see or store your Google password.</li>
              <li><strong>Course Tracking Data:</strong> Which courses you choose to track and your notification preferences</li>
              <li><strong>Usage Data:</strong> How you interact with our service (pages visited, features used), associated with your account</li>
            </ul>
            <p className="mt-2">
              For details on the Purdue course data we read and how we read it, see our{' '}
              <Link to="/about" className="text-slate-800 font-medium underline">
                About &amp; Transparency
              </Link>{' '}
              page. That data is public and contains no personal information about any student.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">2. How We Use Your Information</h2>
            <ul className="list-disc list-outside space-y-1 pl-5">
              <li>To provide course availability notifications via email</li>
              <li>To authenticate your account and maintain security</li>
              <li>To improve our service through analytics</li>
              <li>To communicate important service updates</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">3. Third-Party Services</h2>
            <p className="mb-2">We use the following third-party services:</p>
            <ul className="list-disc list-outside space-y-1 pl-5">
              <li><strong>Resend:</strong> For sending email notifications</li>
              <li><strong>Google:</strong> For "Sign in with Google," if you choose to use it</li>
              <li><strong>Rybbit:</strong> For usage analytics, which receives your account ID and email address so we can tell signed-in sessions apart</li>
              <li><strong>Railway:</strong> For hosting our service</li>
            </ul>
            <p className="mt-2">These services have their own privacy policies governing their use of your data. We do not sell your data or share it with advertisers.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">4. Data Retention</h2>
            <p>
              We retain your data for as long as your account is active. You can request deletion
              of your account and associated data at any time by emailing{' '}
              <a href="mailto:privacy@boilersnipe.com" className="text-slate-800 font-medium underline">
                privacy@boilersnipe.com
              </a>
              .
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">5. Data Security</h2>
            <p className="mb-2">We implement industry-standard security measures including:</p>
            <ul className="list-disc list-outside space-y-1 pl-5">
              <li>Password hashing using bcrypt</li>
              <li>HTTPS encryption for all data transmission</li>
              <li>JWT-based authentication</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">6. Your Rights</h2>
            <p className="mb-2">You have the right to:</p>
            <ul className="list-disc list-outside space-y-1 pl-5">
              <li>Access your personal data</li>
              <li>Correct inaccurate data</li>
              <li>Request deletion of your data</li>
              <li>Export your data</li>
            </ul>
            <p className="mt-2">
              To exercise any of these, email{' '}
              <a href="mailto:privacy@boilersnipe.com" className="text-slate-800 font-medium underline">
                privacy@boilersnipe.com
              </a>
              .
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">7. Cookies and Local Storage</h2>
            <p>
              We store your authentication token and basic account details in your browser's
              localStorage so you stay signed in. Our analytics provider may also store an
              identifier in your browser to distinguish one visit from another. We do not use
              advertising or tracking cookies.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">8. Changes to This Policy</h2>
            <p>We may update this policy from time to time. We will notify you of any significant changes by posting a notice on our website.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">9. Contact</h2>
            <p>
              If you have questions about this privacy policy, contact us at{' '}
              <a href="mailto:privacy@boilersnipe.com" className="text-slate-800 font-medium underline">
                privacy@boilersnipe.com
              </a>
              .
            </p>
          </section>
        </div>
      </div>
    </div>
  );
};

export default Privacy;

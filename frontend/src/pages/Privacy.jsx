import { Link } from 'react-router-dom';

const Privacy = () => {
  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
        <h1 className="text-3xl font-bold text-slate-800 mb-8">Privacy Policy</h1>

        <div className="bg-white rounded-xl border border-slate-200 p-6 sm:p-8 space-y-6 text-slate-600">
          <p className="text-sm text-slate-500">Last updated: August 2026</p>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">1. Information We Collect</h2>
            <p className="mb-2">We collect information you provide directly:</p>
            <ul className="list-disc list-outside space-y-1 pl-5">
              <li><strong>Account Information:</strong> Your email address, plus a password if you register with one. If you use "Sign in with Google," we receive your email address from Google and never see or store your Google password.</li>
              <li><strong>Course Tracking Data:</strong> Which courses you choose to track and your notification preferences</li>
              <li><strong>Usage and Diagnostic Data:</strong> Pages visited, referral and device information, approximate location, selected feature actions, and JavaScript errors. When you are signed in, we associate this data with your account ID and email address.</li>
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
              <li>To understand feature usage and diagnose technical problems</li>
              <li>To communicate important service updates</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">3. Third-Party Services</h2>
            <p className="mb-2">We use the following third-party services:</p>
            <ul className="list-disc list-outside space-y-1 pl-5">
              <li><strong>Resend:</strong> For sending email notifications</li>
              <li><strong>Google:</strong> For "Sign in with Google," if you choose to use it</li>
              <li><strong>Rybbit:</strong> For analytics and error monitoring. Rybbit receives usage data, your account ID, and your email address when you are signed in.</li>
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
              localStorage so you stay signed in. Rybbit also stores your analytics user ID in
              localStorage after you sign in. We do not use advertising or analytics cookies.
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

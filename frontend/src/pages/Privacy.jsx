const Privacy = () => {
  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
        <h1 className="text-3xl font-bold text-slate-800 mb-8">Privacy Policy</h1>

        <div className="bg-white rounded-xl border border-slate-200 p-6 sm:p-8 space-y-6 text-slate-600">
          <p className="text-sm text-slate-500">Last updated: January 2025</p>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">1. Information We Collect</h2>
            <p className="mb-2">We collect information you provide directly:</p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li><strong>Account Information:</strong> Email address and password when you register</li>
              <li><strong>Course Tracking Data:</strong> Which courses you choose to track and your notification preferences</li>
              <li><strong>Usage Data:</strong> How you interact with our service (pages visited, features used)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">2. How We Use Your Information</h2>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>To provide course availability notifications via email</li>
              <li>To authenticate your account and maintain security</li>
              <li>To improve our service through analytics</li>
              <li>To communicate important service updates</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">3. Third-Party Services</h2>
            <p className="mb-2">We use the following third-party services:</p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li><strong>Resend:</strong> For sending email notifications</li>
              <li><strong>Resend:</strong> For sending email notifications</li>
              <li><strong>Railway:</strong> For hosting our service</li>
            </ul>
            <p className="mt-2">These services have their own privacy policies governing their use of your data.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">4. Data Retention</h2>
            <p>We retain your data for as long as your account is active. You can request deletion of your account and associated data at any time by contacting us.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">5. Data Security</h2>
            <p>We implement industry-standard security measures including:</p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>Password hashing using bcrypt</li>
              <li>HTTPS encryption for all data transmission</li>
              <li>JWT-based authentication</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">6. Your Rights</h2>
            <p>You have the right to:</p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>Access your personal data</li>
              <li>Correct inaccurate data</li>
              <li>Request deletion of your data</li>
              <li>Export your data</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">7. Cookies</h2>
            <p>We use localStorage to store your authentication token.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">8. Changes to This Policy</h2>
            <p>We may update this policy from time to time. We will notify you of any significant changes by posting a notice on our website.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">9. Contact</h2>
            <p>If you have questions about this privacy policy, please contact us at privacy@boilersnipe.com</p>
          </section>
        </div>
      </div>
    </div>
  );
};

export default Privacy;

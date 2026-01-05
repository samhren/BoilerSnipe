const Terms = () => {
  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
        <h1 className="text-3xl font-bold text-slate-800 mb-8">Terms of Service</h1>

        <div className="bg-white rounded-xl border border-slate-200 p-6 sm:p-8 space-y-6 text-slate-600">
          <p className="text-sm text-slate-500">Last updated: January 2025</p>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">1. Acceptance of Terms</h2>
            <p>By accessing or using BoilerSnipe, you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use our service.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">2. Description of Service</h2>
            <p>BoilerSnipe is a course seat availability tracking service for Purdue University students. We monitor course seat availability and notify users when seats become available in their tracked courses.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">3. User Accounts</h2>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>You must provide a valid email address to create an account</li>
              <li>You are responsible for maintaining the security of your account</li>
              <li>You must not share your account credentials with others</li>
              <li>You must notify us immediately of any unauthorized access</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">4. Acceptable Use</h2>
            <p className="mb-2">You agree NOT to:</p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>Use the service for any unlawful purpose</li>
              <li>Attempt to gain unauthorized access to our systems</li>
              <li>Interfere with or disrupt the service</li>
              <li>Use automated systems to access the service excessively</li>
              <li>Resell or redistribute the service without permission</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">5. Service Availability</h2>
            <p>We strive to maintain high availability but do not guarantee uninterrupted access. The service may be temporarily unavailable for maintenance or due to factors beyond our control.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">6. No Guarantee of Results</h2>
            <p>While we make every effort to provide accurate and timely notifications, we cannot guarantee:</p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>That you will be able to enroll in a course after receiving a notification</li>
              <li>The accuracy of seat availability data from Purdue's systems</li>
              <li>Delivery of notifications (email delivery depends on third-party services)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">7. Intellectual Property</h2>
            <p>All content, features, and functionality of BoilerSnipe are owned by us and are protected by copyright and other intellectual property laws.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">8. Limitation of Liability</h2>
            <p>TO THE MAXIMUM EXTENT PERMITTED BY LAW, BOILERSNIPE SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING BUT NOT LIMITED TO LOSS OF PROFITS, DATA, OR USE, ARISING FROM YOUR USE OF THE SERVICE.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">9. Disclaimer</h2>
            <p>THE SERVICE IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED. WE DO NOT WARRANT THAT THE SERVICE WILL BE ERROR-FREE OR UNINTERRUPTED.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">10. Termination</h2>
            <p>We reserve the right to terminate or suspend your account at any time for violations of these terms or for any other reason at our discretion.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">11. Changes to Terms</h2>
            <p>We may modify these terms at any time. Continued use of the service after changes constitutes acceptance of the new terms.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">12. Governing Law</h2>
            <p>These terms shall be governed by the laws of the State of Indiana, without regard to its conflict of law provisions.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">13. Contact</h2>
            <p>For questions about these terms, please contact us at legal@boilersnipe.com</p>
          </section>
        </div>
      </div>
    </div>
  );
};

export default Terms;

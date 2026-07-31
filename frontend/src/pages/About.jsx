import { Link } from 'react-router-dom';

const About = () => {
  return (
    <div className="page-shell">
      <div className="mx-auto max-w-3xl px-5 py-12 sm:px-7 sm:py-16">
        <p className="eyebrow mb-3">Independent &amp; open source</p>
        <h1 className="display-title mb-3">About &amp; transparency</h1>
        <p className="mb-9 max-w-2xl text-muted">
          How BoilerSnipe works, exactly what it accesses, and how to reach us.
        </p>

        <div className="legal-copy space-y-7 border-t border-line pt-7">
          <p className="text-sm text-slate-500">Last updated: July 2026</p>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">What BoilerSnipe is</h2>
            <p>
              BoilerSnipe is a free tool built by a Purdue student. It watches Purdue course
              sections that a student has asked it to watch, and sends that student an email when
              a section goes from full to having an open seat.
            </p>
            <p className="mt-2">
              It is free to use, it is not a business, and we have no plans to charge for it or to
              sell anything.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">What data we access</h2>
            <p className="mb-2">
              We read publicly available course pages from Purdue's self-service scheduling system
              at <code className="text-sm bg-slate-100 px-1.5 py-0.5 rounded">selfservice.mypurdue.purdue.edu</code>.
              These pages are served to anyone on the internet without logging in.
            </p>
            <p className="mb-2">From those pages we read only:</p>
            <ul className="list-disc list-outside space-y-1 pl-5">
              <li>The course listing (CRN, course code, title, instructor, meeting time, section)</li>
              <li>The "Registration Availability" table (seat capacity, seats taken, seats remaining)</li>
            </ul>
            <p className="mt-2">
              We do not read, store, or transmit any personal information about any student from
              Purdue's systems, because none is present on the pages we read.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">How often we request pages</h2>
            <ul className="list-disc list-outside space-y-1 pl-5">
              <li>
                Seat checks run on a fixed interval (currently every 5 minutes) and only for course
                sections that at least one signed-in user is actively tracking. We do not poll the
                full catalog for seat counts.
              </li>
              <li>
                A course listing for the current term is collected when our background worker
                starts, and optionally on a weekly schedule, to keep search results current.
              </li>
            </ul>
            <p className="mt-2">
              If Purdue would prefer a lower rate, different hours, or a different approach
              entirely, we will change it. See below.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">How to identify our traffic</h2>
            <p className="mb-2">
              Our requests identify themselves rather than imitating a web browser. They are sent
              with this user agent:
            </p>
            <pre className="text-xs sm:text-sm bg-slate-100 text-slate-700 rounded-lg p-3 overflow-x-auto"><code>BoilerSnipe/1.0 (+https://boilersnipe.com/about; contact@boilersnipe.com)</code></pre>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">What we never do</h2>
            <ul className="list-disc list-outside space-y-1 pl-5">
              <li>We never ask for, store, or use a student's Purdue credentials or Career Account.</li>
              <li>We never log in to myPurdue or any authenticated Purdue system.</li>
              <li>
                We never register, drop, or hold a seat for anyone. BoilerSnipe only sends a
                notification. Registering is something the student does themselves, through Purdue's
                own system.
              </li>
              <li>We never access data that is not already public.</li>
              <li>We never sell user data or share it with advertisers.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">Relationship to Purdue University</h2>
            <p>
              BoilerSnipe is not affiliated with, endorsed by, sponsored by, or connected to Purdue
              University in any way. "Purdue," "Boilermaker," and related names and logos are
              trademarks of their respective owners. We use the name "Purdue" only to describe
              which university's course data the tool covers.
            </p>
          </section>

          <section className="rounded-r-lg border-l-[3px] border-l-deep-gold bg-paper p-5">
            <h2 className="text-xl font-semibold text-slate-800 mb-3">For Purdue faculty, staff, and IT</h2>
            <p className="mb-2">
              If you work for Purdue and have any concern about this tool, please contact us at{' '}
              <a href="mailto:contact@boilersnipe.com" className="text-slate-800 font-medium underline">
                contact@boilersnipe.com
              </a>
              . We will respond quickly.
            </p>
            <p className="mb-2">
              <strong className="text-slate-800">
                If Purdue asks us to reduce our request rate, change how the tool works, or shut it
                down entirely, we will comply immediately and without argument.
              </strong>{' '}
              We would rather be asked than blocked.
            </p>
            <p>
              If Purdue has an official course data feed or API we should be using instead of
              reading public pages, we would much prefer to use it. Please tell us and we will
              migrate.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">Open source</h2>
            <p>
              BoilerSnipe is open source under the MIT license. Anyone can read exactly what it
              does at{' '}
              <a
                href="https://github.com/samhren/BoilerSnipe"
                target="_blank"
                rel="noopener noreferrer"
                className="text-slate-800 font-medium underline"
              >
                github.com/samhren/BoilerSnipe
              </a>
              .
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-800 mb-3">Contact</h2>
            <p>
              General questions:{' '}
              <a href="mailto:contact@boilersnipe.com" className="text-slate-800 font-medium underline">
                contact@boilersnipe.com
              </a>
              <br />
              Privacy:{' '}
              <a href="mailto:privacy@boilersnipe.com" className="text-slate-800 font-medium underline">
                privacy@boilersnipe.com
              </a>
            </p>
            <p className="mt-2">
              See also our{' '}
              <Link to="/privacy" className="text-slate-800 font-medium underline">
                Privacy Policy
              </Link>{' '}
              and{' '}
              <Link to="/terms" className="text-slate-800 font-medium underline">
                Terms of Service
              </Link>
              .
            </p>
          </section>
        </div>
      </div>
    </div>
  );
};

export default About;

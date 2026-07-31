import { forwardRef } from 'react';

const TrackCard = forwardRef(({ track, onDelete, onUpdate }, ref) => {
  const { course } = track;
  const isUpdating = course.seats_capacity === 0 && course.seats_remaining === 0;
  const status = isUpdating
    ? { dot: 'bg-purdue-gold animate-pulse', label: 'Checking availability', color: 'text-muted' }
    : course.seats_remaining > 5
      ? { dot: 'bg-available', label: `${course.seats_remaining} seats available`, color: 'text-available' }
      : course.seats_remaining > 0
        ? { dot: 'bg-limited', label: `${course.seats_remaining} ${course.seats_remaining === 1 ? 'seat' : 'seats'} left`, color: 'text-limited' }
        : { dot: 'bg-muted', label: 'Full', color: 'text-muted' };

  return (
    <article ref={ref} className="scroll-mt-24 border-b border-line p-4 transition-colors duration-500 last:border-0 sm:p-5">
      <div className="grid gap-5 lg:grid-cols-[1.35fr_0.9fr_0.9fr_auto] lg:items-center">
        <div className={course.seats_remaining <= 0 && !isUpdating ? 'text-muted' : ''}>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-sm font-semibold">{course.course_code} · {course.title}</h2>
            {course.schedule_type && <span className="rounded border border-line bg-paper px-2 py-0.5 text-[11px] text-muted">{course.schedule_type}</span>}
          </div>
          <p className="mono-detail mt-1">CRN {course.crn}{course.section ? ` · Section ${course.section}` : ''}</p>
        </div>

        <div className="text-sm">
          <div className="font-mono text-xs">{course.days || 'TBA'} · {course.time || 'TBA'}</div>
          <div className="mt-1 truncate text-xs text-muted">{course.instructor || 'Instructor TBA'}</div>
        </div>

        <div className={`flex items-center gap-2 text-sm ${status.color}`}>
          <span className={`status-dot ${status.dot}`} />
          {status.label}
        </div>

        <div className="flex flex-wrap items-center gap-x-5 gap-y-3 lg:justify-end">
          <label className="flex cursor-pointer items-center gap-2 text-xs text-muted">
            Notify on open
            <span className="relative inline-flex">
              <input type="checkbox" checked={track.notify_on_open} onChange={(e) => onUpdate(track.id, { notify_on_open: e.target.checked })} className="peer sr-only" />
              <span className="h-[22px] w-[38px] rounded-full bg-line transition-colors peer-checked:bg-deep-gold" />
              <span className="absolute left-0.5 top-0.5 h-[18px] w-[18px] rounded-full bg-canvas transition-transform peer-checked:translate-x-4" />
            </span>
          </label>
          <button onClick={() => onDelete(track.id)} className="min-h-11 text-xs font-semibold text-danger hover:text-red-700">Stop watching</button>
        </div>
      </div>
      <label className="mt-3 flex cursor-pointer items-center gap-2 border-t border-line pt-3 text-xs text-muted lg:ml-auto lg:w-fit lg:border-0 lg:pt-0">
        <input type="checkbox" checked={track.notify_on_close} onChange={(e) => onUpdate(track.id, { notify_on_close: e.target.checked })} className="accent-deep-gold" />
        Also notify me when this section closes
      </label>
    </article>
  );
});

TrackCard.displayName = 'TrackCard';

export default TrackCard;

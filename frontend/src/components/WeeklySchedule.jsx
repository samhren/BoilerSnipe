import React, { useMemo } from 'react';

const DAYS = ['M', 'T', 'W', 'R', 'F'];
const DAYS_FULL = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const START_HOUR = 7; // 7 AM
const END_HOUR = 18; // 6 PM
const TOTAL_HOURS = END_HOUR - START_HOUR + 1;

const WeeklySchedule = ({ tracks }) => {
    const scheduleData = useMemo(() => {
        const events = [];

        tracks.forEach(track => {
            const { course } = track;
            if (!course.days || !course.time || course.days === 'TBA' || course.time === 'TBA') return;

            // Parse time: "10:30 am - 11:20 am"
            const timeParts = course.time.split(' - ');
            if (timeParts.length !== 2) return;

            const parseTime = (timeStr) => {
                const [time, modifier] = timeStr.split(' ');
                let [hours, minutes] = time.split(':').map(Number);
                if (modifier === 'pm' && hours < 12) hours += 12;
                if (modifier === 'am' && hours === 12) hours = 0;
                return hours * 60 + minutes;
            };

            const startMinutes = parseTime(timeParts[0]);
            const endMinutes = parseTime(timeParts[1]);

            // Filter out if times are completely outside our view range (optional, but good for safety)
            // For now we'll just clamp or let it overflow if we use absolute positioning

            // Parse days: "MWF", "TR"
            for (let i = 0; i < course.days.length; i++) {
                const char = course.days[i];
                const dayIndex = DAYS.indexOf(char);
                if (dayIndex !== -1) {
                    events.push({
                        id: track.id,
                        courseCode: course.course_code,
                        title: course.title,
                        dayIndex,
                        startMinutes,
                        duration: endMinutes - startMinutes,
                        color: 'bg-indigo-100 border-indigo-200 text-indigo-800' // Can rotate colors later
                    });
                }
            }
        });

        return events;
    }, [tracks]);

    if (scheduleData.length === 0) return null;

    return (
        <div className="bg-white rounded-xl border border-slate-200 p-4 sm:p-6 mb-6 overflow-hidden">
            <h2 className="text-lg font-bold text-slate-800 mb-4">Weekly Schedule</h2>

            <div className="relative overflow-x-auto">
                <div className="min-w-[600px] relative">
                    {/* Header */}
                    <div className="grid grid-cols-6 mb-2">
                        <div className="text-xs text-slate-400 font-medium text-right pr-2"></div>
                        {DAYS_FULL.map(day => (
                            <div key={day} className="text-sm font-semibold text-slate-600 text-center uppercase tracking-wider text-xs">
                                {day.slice(0, 3)}
                            </div>
                        ))}
                    </div>

                    {/* Grid */}
                    <div className="relative grid grid-cols-6 border-t border-slate-200" style={{ height: '500px' }}>

                        {/* Time labels and horizontal lines */}
                        <div className="col-span-6 relative h-full">
                            {Array.from({ length: TOTAL_HOURS }).map((_, i) => {
                                const hour = START_HOUR + i;
                                const displayHour = hour > 12 ? hour - 12 : hour;
                                const ampm = hour >= 12 ? 'PM' : 'AM';
                                const top = (i / TOTAL_HOURS) * 100;

                                return (
                                    <div key={hour} className="absolute w-full border-b border-slate-100 flex items-center" style={{ top: `${top}%`, height: `${100 / TOTAL_HOURS}%` }}>
                                        <div className="w-[16.666%] text-right pr-2 text-xs text-slate-400 -mt-[calc(100%)] transform -translate-y-1/2">
                                            {displayHour} {ampm}
                                        </div>
                                        {/* Vertical grid lines for days */}
                                        <div className="absolute left-[16.666%] w-px h-full bg-slate-100"></div>
                                        <div className="absolute left-[33.333%] w-px h-full bg-slate-100"></div>
                                        <div className="absolute left-[50%] w-px h-full bg-slate-100"></div>
                                        <div className="absolute left-[66.666%] w-px h-full bg-slate-100"></div>
                                        <div className="absolute left-[83.333%] w-px h-full bg-slate-100"></div>
                                    </div>
                                );
                            })}
                        </div>

                        {/* Events */}
                        <div className="absolute inset-x-0 bottom-0 left-[16.666%] w-[83.333%] h-full">
                            {/* This container aligns with the days columns Monday-Friday */}
                            {scheduleData.map((event, idx) => {
                                // Calculate position percentage
                                // Total minutes in shown day = TOTAL_HOURS * 60
                                // Start of day in minutes = START_HOUR * 60

                                const totalDayMinutes = TOTAL_HOURS * 60;
                                const displayStartMinutes = START_HOUR * 60;

                                const relativeStart = Math.max(0, event.startMinutes - displayStartMinutes);
                                const top = (relativeStart / totalDayMinutes) * 100;
                                const height = (event.duration / totalDayMinutes) * 100;

                                // Day column width is 20% (100% / 5 days)
                                const left = (event.dayIndex * 20);

                                return (
                                    <div
                                        key={`${event.id}-${idx}`}
                                        className={`absolute rounded px-1 py-0.5 border text-xs overflow-hidden hover:z-10 transition-all hover:shadow-md cursor-default ${event.color}`}
                                        style={{
                                            top: `${top}%`,
                                            height: `${height}%`,
                                            left: `${left}%`,
                                            width: '19%', // Slight gap
                                            margin: '0.5%'
                                        }}
                                        title={`${event.courseCode}: ${event.title}`}
                                    >
                                        <div className="font-bold truncate">{event.courseCode}</div>
                                        <div className="truncate opacity-75 hidden sm:block">{event.title}</div>
                                    </div>
                                );
                            })}
                        </div>

                    </div>
                </div>
            </div>
        </div>
    );
};

export default WeeklySchedule;

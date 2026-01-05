import React, { useMemo } from 'react';

const DAYS = ['M', 'T', 'W', 'R', 'F'];
const DAYS_FULL = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const START_HOUR = 7; // 7 AM
const END_HOUR = 18; // 6 PM
const TOTAL_HOURS = END_HOUR - START_HOUR + 1;

const WeeklySchedule = ({ tracks, onEventClick }) => {
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
                        instructor: course.instructor, // Add instructor
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

    const totalHeight = 400; // Reduced height for compactness

    if (scheduleData.length === 0) return null;

    return (
        <div className="bg-white rounded-xl border border-slate-200 p-4 mb-6 overflow-hidden">
            <h2 className="text-lg font-bold text-slate-800 mb-2">Weekly Schedule</h2>

            <div className="flex relative items-stretch" style={{ height: `${totalHeight}px` }}>

                {/* Time Column - Compact */}
                <div className="w-10 flex-shrink-0 relative border-r border-slate-100 mr-1 text-[10px] text-slate-400 font-medium">
                    {Array.from({ length: TOTAL_HOURS }).map((_, i) => {
                        const hour = START_HOUR + i;
                        const displayHour = hour > 12 ? hour - 12 : hour;
                        const ampm = hour >= 12 ? 'pm' : 'am';
                        const top = (i / TOTAL_HOURS) * 100;

                        // Don't show last hour label to avoid overflow
                        if (i === TOTAL_HOURS - 1) return null;

                        return (
                            <div key={hour} className="absolute w-full text-right pr-1" style={{ top: `${top}%`, transform: 'translateY(-50%)' }}>
                                {displayHour}{ampm}
                            </div>
                        );
                    })}
                </div>

                {/* Days Grid - Scrollable on mobile */}
                <div className="flex-1 relative overflow-x-auto no-scrollbar">
                    <div className="flex min-w-[600px] h-full relative">
                        {DAYS_FULL.map((day, dayIdx) => (
                            <div key={day} className="flex-1 relative border-r border-slate-50 last:border-0">
                                {/* Day Header */}
                                <div className="text-center text-xs font-semibold text-slate-600 uppercase py-1 border-b border-slate-100 bg-slate-50/50 absolute top-0 w-full z-10 h-6">
                                    {window.innerWidth < 640 ? day.slice(0, 1) : day.slice(0, 3)}
                                </div>

                                {/* Horizontal Grid Lines */}
                                <div className="absolute inset-0 pt-6">
                                    {Array.from({ length: TOTAL_HOURS }).map((_, i) => (
                                        <div
                                            key={i}
                                            className="absolute w-full border-b border-slate-50"
                                            style={{ top: `${(i / TOTAL_HOURS) * 100}%` }}
                                        ></div>
                                    ))}
                                </div>

                                {/* Events for this day */}
                                <div className="absolute inset-0 pt-6">
                                    {scheduleData
                                        .filter(event => event.dayIndex === dayIdx)
                                        .map((event, idx) => {
                                            const totalDayMinutes = TOTAL_HOURS * 60;
                                            const displayStartMinutes = START_HOUR * 60;
                                            const relativeStart = Math.max(0, event.startMinutes - displayStartMinutes);
                                            const top = (relativeStart / totalDayMinutes) * 100;
                                            const height = (event.duration / totalDayMinutes) * 100;

                                            return (
                                                <div
                                                    key={`${event.id}-${idx}`}
                                                    onClick={() => onEventClick && onEventClick(event.id)}
                                                    className={`absolute inset-x-0.5 rounded px-1 py-0.5 border text-[10px] sm:text-xs overflow-hidden hover:z-20 hover:ring-2 hover:ring-indigo-400 hover:shadow-lg transition-all cursor-pointer ${event.color}`}
                                                    style={{
                                                        top: `${top}%`,
                                                        height: `${height}%`,
                                                    }}
                                                >
                                                    <div className="font-bold truncate leading-tight">{event.courseCode}</div>
                                                    <div className="truncate opacity-75 hidden sm:block leading-tight text-[9px] sm:text-[10px]">{event.instructor}</div>
                                                </div>
                                            );
                                        })}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default WeeklySchedule;

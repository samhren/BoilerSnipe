import React, { useMemo, useState } from 'react';

const DAYS = ['M', 'T', 'W', 'R', 'F'];
const DAYS_FULL = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const START_HOUR = 7; // 7 AM
const END_HOUR = 18; // 6 PM
const TOTAL_HOURS = END_HOUR - START_HOUR + 1;

const WeeklySchedule = ({ tracks, onEventClick }) => {
    const [isExpanded, setIsExpanded] = useState(false);

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
                        color: 'bg-paper border-purdue-gold text-ink'
                    });
                }
            }
        });

        return events;
    }, [tracks]);

    const totalHeight = 400; // Reduced height for compactness

    if (scheduleData.length === 0) return null;

    return (
        <div
            className={`surface mb-7 cursor-pointer overflow-hidden p-4 transition-all duration-300 sm:p-5 ${isExpanded ? '' : 'hover:bg-paper'}`}
            onClick={() => setIsExpanded(!isExpanded)}
        >
            <div className="flex justify-between items-center mb-2">
                <div>
                    <p className="eyebrow mb-1">At a glance</p>
                    <h2 className="font-display text-xl font-medium text-ink">Weekly schedule</h2>
                </div>
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={2}
                    stroke="currentColor"
                    className={`h-5 w-5 text-muted transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
                >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                </svg>
            </div>

            {isExpanded && (
                <div
                    className="flex relative items-stretch animate-in fade-in slide-in-from-top-2 duration-300"
                    style={{ height: `${totalHeight}px` }}
                    onClick={(e) => e.stopPropagation()} // Prevent collapse when interacting with the schedule itself
                >

                    {/* Time Column - Compact */}
                    <div className="relative mr-1 w-10 flex-shrink-0 border-r border-line font-mono text-[10px] font-medium text-muted">
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
                                <div key={day} className="relative flex-1 border-r border-line last:border-0">
                                    {/* Day Header */}
                                    <div className="absolute top-0 z-10 h-6 w-full border-b border-line bg-paper py-1 text-center font-mono text-[10px] font-medium uppercase text-muted">
                                        <span className="sm:hidden">{day.slice(0, 1)}</span><span className="hidden sm:inline">{day.slice(0, 3)}</span>
                                    </div>

                                    {/* Horizontal Grid Lines */}
                                    <div className="absolute inset-0 pt-6">
                                        {Array.from({ length: TOTAL_HOURS }).map((_, i) => (
                                            <div
                                                key={i}
                                                className="absolute w-full border-b border-line/60"
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
                                                        onClick={(e) => {
                                                            e.stopPropagation(); // Ensure event click doesn't trigger parent/other handlers if undesired
                                                            if (onEventClick) onEventClick(event.id);
                                                        }}
                                                        className={`absolute inset-x-0.5 cursor-pointer overflow-hidden rounded border px-1 py-0.5 text-[10px] transition-all hover:z-20 hover:ring-2 hover:ring-purdue-gold sm:text-xs ${event.color}`}
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
            )}
        </div>
    );
};

export default WeeklySchedule;

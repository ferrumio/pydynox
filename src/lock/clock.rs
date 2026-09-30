//! Conservative owner validity without comparing clocks on different hosts.

use std::time::{Duration, Instant, SystemTime};

#[derive(Clone, Copy)]
pub(super) struct Stamp {
    pub monotonic: Instant,
    wall: SystemTime,
}

impl Stamp {
    pub fn now() -> Self {
        Self {
            monotonic: Instant::now(),
            wall: SystemTime::now(),
        }
    }

    pub fn valid(&self, lease: Duration) -> bool {
        self.valid_at(lease, Instant::now(), SystemTime::now())
    }

    fn valid_at(&self, lease: Duration, monotonic: Instant, wall: SystemTime) -> bool {
        // Reserve 10% for bounded clock-rate differences. The wall clock also
        // catches host suspension on platforms whose monotonic clock pauses.
        // Clock jumps can shorten validity, never extend the monotonic budget.
        let budget = lease.mul_f64(0.9);
        monotonic
            .checked_duration_since(self.monotonic)
            .is_some_and(|elapsed| elapsed < budget)
            && wall
                .duration_since(self.wall)
                .is_ok_and(|elapsed| elapsed < budget)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validity_requires_both_clocks_inside_the_margin() {
        let stamp = Stamp::now();
        let lease = Duration::from_secs(30);
        for (mono, wall, expected) in [
            (0.0, 0.0, true),
            (26.9, 26.9, true),
            (27.0, 26.0, false),
            (26.0, 27.0, false),
            (31.0, 31.0, false),
            (1.0, 60.0, false), // Whole-host suspension or forward clock jump.
            (31.0, 1.0, false), // Backward jump cannot extend monotonic validity.
        ] {
            assert_eq!(
                stamp.valid_at(
                    lease,
                    stamp.monotonic + Duration::from_secs_f64(mono),
                    stamp.wall + Duration::from_secs_f64(wall)
                ),
                expected
            );
        }
        assert!(!stamp.valid_at(
            lease,
            stamp.monotonic + Duration::from_secs(1),
            stamp.wall - Duration::from_secs(1)
        ));
    }
}

"""新环境版本门槛和个人券配置的关键回归。无需云调用。"""
import unittest
from datetime import datetime,timedelta,timezone
from preflight import require_release
from configure_lab import build_config

class Setup(unittest.TestCase):
    def test_exact_openeuler_2403(self):
        fields=require_release('ID="openEuler"\nVERSION_ID="24.03"\nNAME="openEuler"','24.03')
        self.assertEqual(fields['VERSION_ID'],'24.03')
    def test_old_release_rejected(self):
        with self.assertRaises(ValueError):
            require_release('ID=openEuler\nVERSION_ID="20.03"','24.03')
    def test_hce_not_openeuler(self):
        with self.assertRaises(ValueError):
            require_release('ID=hce\nVERSION_ID="24.03"','24.03')
    def test_personal_expiry_and_limits(self):
        expiry=(datetime.now(timezone.utc)+timedelta(days=7)).isoformat()
        cfg=build_config(expiry,1.0,6)
        self.assertEqual(cfg['coupon_expires_at'],expiry)
        self.assertEqual(cfg['max_total_requests'],6)
    def test_expired_or_naive_rejected(self):
        for expiry in ['2020-01-01T00:00:00+08:00','2099-01-01T00:00:00']:
            with self.assertRaises(ValueError):build_config(expiry)

if __name__=='__main__':unittest.main()

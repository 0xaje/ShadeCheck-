"""Synthetic prerequisite failures; never application privacy evidence."""
import subprocess
import unittest
from unittest.mock import patch
from shadecheck.doctor import inspect


class DoctorBoundaries(unittest.TestCase):
    def test_client_without_running_engine_is_blocked(self):
        results=[subprocess.CompletedProcess([],1,'','cannot connect'),subprocess.CompletedProcess([],0,'2.40.0','')]
        with patch('shadecheck.doctor.subprocess.run',side_effect=results): result=inspect()
        self.assertEqual(result['status'],'BLOCKED')
        self.assertFalse(result['checks'][1]['ok'])

    def test_windows_engine_cannot_satisfy_linux_container_requirement(self):
        results=[subprocess.CompletedProcess([],0,'windows',''),subprocess.CompletedProcess([],0,'v2.40.0','')]
        with patch('shadecheck.doctor.subprocess.run',side_effect=results): result=inspect()
        self.assertEqual(result['status'],'BLOCKED')

    def test_ready_means_only_prerequisites(self):
        results=[subprocess.CompletedProcess([],0,'linux',''),subprocess.CompletedProcess([],0,'v2.40.0','')]
        with patch('shadecheck.doctor.subprocess.run',side_effect=results): result=inspect()
        self.assertEqual(result['status'],'READY')
        self.assertIn('does not validate',result['scope'])

import logging
import unittest
import errno

from decorators import retry


class RetryableError(Exception):
    pass


class AnotherRetryableError(Exception):
    pass


class UnexpectedError(Exception):
    pass


class RetryTestCase(unittest.TestCase):

    def _no_retry_required(self, exception):
        self.counter = 0

        @retry(exception, tries=4, delay=0.1)
        def succeeds():
            self.counter += 1
            return 'success'

        r = succeeds()

        self.assertEqual(r, 'success')
        self.assertEqual(self.counter, 1)
    def test_no_retry_required_type(self):
        self._no_retry_required(RetryableError)
    def test_no_retry_required_instance(self):
        self._no_retry_required(RetryableError())

    def _retries_once(self, exception):
        self.counter = 0

        @retry(exception, tries=4, delay=0.1)
        def fails_once():
            self.counter += 1
            if self.counter < 2:
                raise RetryableError('failed')
            else:
                return 'success'

        r = fails_once()
        self.assertEqual(r, 'success')
        self.assertEqual(self.counter, 2)
    def test_retries_once_type(self):
        self._retries_once(RetryableError)
    def test_retries_once_instance(self):
        self._retries_once(RetryableError('failed'))

    def _limit_is_reached(self, exception):
        self.counter = 0

        @retry(exception, tries=4, delay=0.1)
        def always_fails():
            self.counter += 1
            raise RetryableError('failed')

        with self.assertRaises(RetryableError):
            always_fails()
        self.assertEqual(self.counter, 4)
    def test_limit_is_reached_type(self):
        self._limit_is_reached(RetryableError)
    def test_limit_is_reached_instance(self):
        self._limit_is_reached(RetryableError('failed'))

    def _multiple_exception_types(self, exceptions):
        self.counter = 0

        @retry(exceptions, tries=4, delay=0.1)
        def raise_multiple_exceptions():
            self.counter += 1
            if self.counter == 1:
                raise RetryableError('a retryable error')
            elif self.counter == 2:
                raise AnotherRetryableError('another retryable error')
            else:
                return 'success'

        r = raise_multiple_exceptions()
        self.assertEqual(r, 'success')
        self.assertEqual(self.counter, 3)
    def test_multiple_exception_types_type(self):
        self._multiple_exception_types((RetryableError, AnotherRetryableError))
    def test_multiple_exception_types_instance(self):
        self._multiple_exception_types((RetryableError('a retryable error'), AnotherRetryableError('another retryable error')))
    def test_multiple_exception_types_mixed1(self):
        self._multiple_exception_types((RetryableError, AnotherRetryableError('another retryable error')))
    def test_multiple_exception_types_mixed2(self):
        self._multiple_exception_types((RetryableError('a retryable error'), AnotherRetryableError))

    def _unexpected_exception_does_not_retry(self, exception):

        @retry(exception, tries=4, delay=0.1)
        def raise_unexpected_error():
            raise UnexpectedError('unexpected error')

        with self.assertRaises(UnexpectedError):
            raise_unexpected_error()
    def test_unexpected_exception_does_not_retry_type(self):
        self._unexpected_exception_does_not_retry(RetryableError)
    def test_unexpected_exception_does_not_retry_instance(self):
        self._unexpected_exception_does_not_retry(RetryableError())

    def _specific_exception(self, exception, expect_success):
        self.counter = 0

        @retry((AnotherRetryableError, RetryableError(errno.ECOMM), UnexpectedError), tries=4, delay=0.1)
        def fails_once():
            self.counter += 1
            if self.counter < 2:
                # The passed exception is an instance, not a type - needed so we can
                # test that we only catch the instances specified, not all instances of the same type
                raise exception
            else:
                return 'success'

        if expect_success:
            # should retry once, with exception swallowed, and then succeed
            r = fails_once()
            self.assertEqual(r, 'success')
            self.assertEqual(self.counter, 2)
        else:
            # the exception shouldn't be swallowed, will fail first time
            # assertRaises needs an exception type, not an instance
            with self.assertRaises(type(exception)):
                fails_once()
            self.assertEqual(self.counter, 1)

    def test_specific_exception_type_uncaught(self):
        # an exception type we don't catch, without args
        self._specific_exception(ValueError(), False)
    def test_specific_exception_type_caught1(self):
        # an exception type we do catch, without args
        self._specific_exception(AnotherRetryableError(), True)
    def test_specific_exception_type_caught2(self):
        # the other exception type we do catch, without args
        self._specific_exception(UnexpectedError(), True)
    def test_specific_exception_instance_caught1(self):
        # an exception type we do catch, with args we should catch
        self._specific_exception(RetryableError(errno.ECOMM), True)
    def test_specific_exception_instance_caught2(self):
        # an exception type we do catch, but with args specified
        self._specific_exception(AnotherRetryableError(errno.ECOMM), True)
    def test_specific_exception_instance_uncaught1(self):
        # an exception type we don't catch, but with args matching those we do catch for another exception
        self._specific_exception(ValueError(errno.ECOMM), False)
    def test_specific_exception_instance_uncaught2(self):
        # an exception type we do catch, but with args we don't catch
        self._specific_exception(RetryableError(errno.EINVAL), False)

    def test_using_a_logger(self):
        self.counter = 0

        sh = logging.StreamHandler()
        logger = logging.getLogger(__name__)
        logger.addHandler(sh)

        @retry(RetryableError, tries=4, delay=0.1, logger=logger)
        def fails_once():
            self.counter += 1
            if self.counter < 2:
                raise RetryableError('failed')
            else:
                return 'success'

        fails_once()


if __name__ == '__main__':
    unittest.main()

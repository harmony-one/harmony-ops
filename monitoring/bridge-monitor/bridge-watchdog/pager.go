package main

import (
	pd "github.com/PagerDuty/go-pagerduty"
)

func notify(serviceKey, msg string) error {
	_, err := pd.CreateEvent(pd.Event{
		Type:        "trigger",
		ServiceKey:  serviceKey,
		Description: msg,
	})
	return err
}

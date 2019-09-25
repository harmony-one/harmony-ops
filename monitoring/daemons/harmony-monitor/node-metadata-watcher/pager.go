package main

import (
	"fmt"

	pd "github.com/PagerDuty/go-pagerduty"
)

func notify(serviceKey, msg string) error {
	resp, err := pd.CreateEvent(pd.Event{
		Type:        "trigger",
		ServiceKey:  serviceKey,
		Description: msg,
	})
	fmt.Println(resp, err)
	return err
}

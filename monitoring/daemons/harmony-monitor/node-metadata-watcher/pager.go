package main

import (
	"fmt"

	pd "github.com/PagerDuty/go-pagerduty"
)

func notifyTeam(serviceKey string) {
	e := pd.Event{
		Type:        "trigger",
		ServiceKey:  serviceKey,
		Description: "Example event -- Edgar testing",
	}
	resp, err := pd.CreateEvent(e)
	fmt.Println(resp, err)
}
